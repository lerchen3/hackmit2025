# serve command:
# vllm serve Qwen/Qwen3-8B --host 0.0.0.0 --port 8000 --dtype auto --max-model-len 8192 --api-key test-123


# run script: python3 test/stream_inference.py


# stop server: pkill -f "vllm serve"
from openai import OpenAI
import os
import json


# vLLM OpenAI-compatible endpoint
base_url = os.getenv("VLLM_BASE_URL", "http://localhost:8000/v1")
api_key = os.getenv("VLLM_API_KEY", "test-123")


client = OpenAI(base_url=base_url, api_key=api_key)


messages = [{"role": "user", "content": "What's 1+1?"}]


stream = client.chat.completions.create(
    model="Qwen/Qwen3-8B",
    messages=messages,
    max_tokens=4096,
    temperature=0.7,
    # Helps some models (e.g., Qwen) by appending the generation start in the template
    stream=True,
)


for chunk in stream:
    if chunk.choices and len(chunk.choices) > 0:
        delta = chunk.choices[0].delta
        if getattr(delta, "content", None):
            print(delta.content, end="", flush=True)


print()