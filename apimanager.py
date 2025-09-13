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
                    # remove routing key from payload before forwarding
                    payload = {k: v for k, v in data.items() if k != "provider"}

                # Execute request
                if provider == "local":
                    resp = self.vllm.chat.completions.create(**payload)
                    return resp.choices[0].message.content
                elif provider == "openai":
                    if isinstance(data, dict):
                        resp = self.openai.chat.completions.create(**payload)
                    else:
                        # Otherwise, assume it's a messages list and use a default model
                        resp = self.openai.chat.completions.create(model="gpt-4o-mini", messages=data)
                    return resp.choices[0].message.content
                else:
                    raise ValueError(f"Unsupported provider: {provider}")
            except Exception as e:
                print(f"Error querying API: {str(e)}. Attempt {i+1} of {APIManager.ATTEMPTS}")
        print(f"Failed to query API after {APIManager.ATTEMPTS} attempts.")
        return None

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
            text = api.query(t["payload"])  # query now returns plain text
            print(f"[{t['name']}] {text}")
        except Exception as e:
            print(f"[{t['name']}] Error: {e}")

    # Embedding test
    try:
        vector = api.embedText("Hello world")
        print(f"[Embedding] dim={len(vector)} first5={vector[:5]}")
    except Exception as e:
        print(f"[Embedding] Error: {e}")