from openai import OpenAI
import os

class APIManager:
    ATTEMPTS = 3
    def __init__(self, api_key=None):
        # Fetch keys from environment if not provided
        openai_key = api_key or os.getenv("OPENAI_API_KEY")

        self.openai_api_key = openai_key

        # OpenAI client
        self.openai = OpenAI(api_key=openai_key)

        # Local vLLM client (OpenAI-compatible)
        self.vllm = OpenAI(
            base_url=os.getenv("VLLM_BASE_URL", "http://localhost:8000/v1"),
            api_key=os.getenv("VLLM_API_KEY", "test-123")
        )

        # Usage tracking and debug flag
        self.last_usage = None
        self.debug_tokens = False

    # Embeds text into vector, returns None if failed
    def embedText(self, text):
        for i in range(0,APIManager.ATTEMPTS):
            try:
                return self.openai.embeddings.create(input=text, model="text-embedding-3-large").data[0].embedding
            except Exception as e:
                print(f"Error embedding text: {str(e)}. Attempt {i+1} of {APIManager.ATTEMPTS}")
        print(f"Failed to embed text through API after {APIManager.ATTEMPTS} attempts.")
        return None
    
    # Query chat completions; accepts either full JSON payload (dict) or messages list
    # If a dict includes key "provider", routes to that provider: "openai" | "local"
    def query(self, data):
        for i in range(0,APIManager.ATTEMPTS):
            try:
                provider = "openai"
                payload = data
                if isinstance(data, dict):
                    provider = data.get("provider", "openai").lower()
                    debug_tokens = data.get("debug_tokens", self.debug_tokens)
                    payload = {k: v for k, v in data.items() if k not in ("provider", "debug_tokens")}
                else:
                    debug_tokens = self.debug_tokens

                # Execute request
                if provider == "local":
                    resp = self.vllm.chat.completions.create(**payload)
                elif provider == "openai":
                    if isinstance(data, dict):
                        resp = self.openai.chat.completions.create(**payload)
                    else:
                        resp = self.openai.chat.completions.create(model="gpt-4o-mini", messages=data)
                else:
                    raise ValueError(f"Unsupported provider: {provider}")

                text = resp.choices[0].message.content
                self.last_usage = getattr(resp, "usage", None)

                if debug_tokens and self.last_usage is not None:
                    counts = self.get_last_token_counts()
                    if counts is not None:
                        print(f"[{provider}] tokens prompt={counts['prompt']} completion={counts['completion']} total={counts['total']}")

                return text
            except Exception as e:
                print(f"Error querying API: {str(e)}. Attempt {i+1} of {APIManager.ATTEMPTS}")
        print(f"Failed to query API after {APIManager.ATTEMPTS} attempts.")
        return None

    # Stream chat completions; yields text chunks. Accepts same payload as query.
    # If debug_tokens True, prints usage at end when available.
    def stream(self, data):
        provider = "openai"
        payload = data
        if isinstance(data, dict):
            provider = data.get("provider", "openai").lower()
            debug_tokens = data.get("debug_tokens", self.debug_tokens)
            payload = {k: v for k, v in data.items() if k not in ("provider", "debug_tokens")}
        else:
            debug_tokens = self.debug_tokens

        # Ensure stream flags for providers that support it
        payload["stream"] = True
        # Ask OpenAI SDK to include usage in the final stream event when possible
        if provider == "openai":
            payload.setdefault("stream_options", {"include_usage": True})

        self.last_usage = None

        try:
            if provider == "local":
                resp_stream = self.vllm.chat.completions.create(**payload)
            elif provider == "openai":
                resp_stream = self.openai.chat.completions.create(**payload)
            else:
                raise ValueError(f"Unsupported provider: {provider}")

            for chunk in resp_stream:
                try:
                    # Stream incremental content
                    delta = chunk.choices[0].delta
                    content = getattr(delta, "content", None)
                    if content:
                        yield content
                    # Capture usage if the SDK provides it during the final event
                    usage = getattr(chunk, "usage", None)
                    if usage is not None:
                        self.last_usage = usage
                except Exception:
                    # Be robust to any chunk variations
                    pass

            # After stream ends, optionally print token counts
            if debug_tokens and self.last_usage is not None:
                counts = self.get_last_token_counts()
                if counts is not None:
                    print(f"[{provider}] tokens prompt={counts['prompt']} completion={counts['completion']} total={counts['total']}")
        except Exception as e:
            print(f"Error streaming API: {str(e)}")

    def _get_usage_value(self, usage, names):
        for n in names:
            try:
                value = getattr(usage, n)
                if value is not None:
                    return value
            except Exception:
                pass
            if isinstance(usage, dict) and n in usage:
                value = usage.get(n)
                if value is not None:
                    return value
        return None

    def get_last_token_counts(self):
        usage = self.last_usage
        if usage is None:
            return None
        prompt = self._get_usage_value(usage, ["prompt_tokens", "input_tokens"])
        completion = self._get_usage_value(usage, ["completion_tokens", "output_tokens"])
        total = self._get_usage_value(usage, ["total_tokens"])
        if total is None and prompt is not None and completion is not None:
            total = prompt + completion
        return {"prompt": prompt, "completion": completion, "total": total}

if __name__ == "__main__":
    api = APIManager()

    tests = [
        {
            "name": "OpenAI",
            "provider": "openai",
            "payload": {
                "provider": "openai",
                "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                "messages": [{"role": "user", "content": "Say hi in 1 word."}],
                "max_tokens": 16,
            },
        },
        {
            "name": "Local vLLM",
            "provider": "local",
            "payload": {
                "provider": "local",
                "model": os.getenv("VLLM_MODEL", "Qwen/Qwen3-8B"),
                "messages": [{"role": "user", "content": "Say hi in 1 word."}],
                "max_tokens": 64,
                "temperature": 0.7,
            },
        },
    ]

    for t in tests:
        try:
            t["payload"]["debug_tokens"] = True
            text = api.query(t["payload"])  # query now returns plain text
            print(f"[{t['name']}] {text}")
            counts = api.get_last_token_counts()
            if counts is not None:
                print(f"[{t['name']}] tokens prompt={counts['prompt']} completion={counts['completion']} total={counts['total']}")
        except Exception as e:
            print(f"[{t['name']}] Error: {e}")

    # Embedding test
    try:
        vector = api.embedText("Hello world")
        print(f"[Embedding] dim={len(vector)} first5={vector[:5]}")
    except Exception as e:
        print(f"[Embedding] Error: {e}")