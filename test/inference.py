# serve command:
# vllm serve Qwen/Qwen3-8B --host 0.0.0.0 --port 8000 --dtype auto --max-model-len 8192 --api-key test-123


# run script: python3 test/inference.py


# stop server: pkill -f "vllm serve"
from openai import OpenAI
import os
import json


# vLLM OpenAI-compatible endpoint
base_url = os.getenv("VLLM_BASE_URL", "http://localhost:8000/v1")
api_key = os.getenv("VLLM_API_KEY", "test-123")


client = OpenAI(base_url=base_url, api_key=api_key)

messages = [{"role": "user", "content": "What's 1+1?"}]


resp = client.chat.completions.create(
    model="Qwen/Qwen3-8B",
    messages=messages,
    max_tokens=4096,
    temperature=0.7,
)

print(resp.choices[0].message.content.strip())