import argparse
import json
import os
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

from generate import QN
from openai import OpenAI


def make_payload(model: str, temperature: float):
    return {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful math problem solver. Provide reasoning briefly and a final numeric answer.",
            },
            {"role": "user", "content": QN.strip()},
        ],
        "temperature": temperature,
        "top_p": 0.95,
        "max_tokens": 8192,
    }


def main():
    parser = argparse.ArgumentParser(description="Run the math prompt N times against vLLM and save outputs to JSONL.")
    parser.add_argument("--n", type=int, default=1000, help="Number of runs")
    parser.add_argument(
        "--out",
        type=str,
        default=os.path.abspath("/home/ubuntu/hackmit2025/prompt_runs.jsonl"),
        help="Output JSONL path",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=os.getenv("VLLM_MODEL", "Qwen/Qwen3-30B-A3B"),
        help="vLLM model name (default from VLLM_MODEL or Qwen/Qwen3-30B-A3B)",
    )
    parser.add_argument("--temperature", type=float, default=1.0)
    parser.add_argument("--concurrency", type=int, default=20)
    parser.add_argument(
        "--base-url",
        type=str,
        default=os.getenv("VLLM_BASE_URL", "http://localhost:8000/v1"),
        help="vLLM OpenAI-compatible base URL",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=os.getenv("VLLM_API_KEY", "test-123"),
        help="Dummy API key for vLLM server (ignored by most setups)",
    )
    args = parser.parse_args()

    # vLLM OpenAI-compatible client
    client = OpenAI(base_url=args.base_url, api_key=args.api_key)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    lock = Lock()

    def job(i: int):
        payload = make_payload(args.model, args.temperature)
        try:
            resp = client.chat.completions.create(**payload)
            text = resp.choices[0].message.content or ""
        except Exception:
            text = ""
        return {
            "index": i,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "backend": "vllm",
            "model": args.model,
            "temperature": args.temperature,
            "output": text,
        }

    with ThreadPoolExecutor(max_workers=max(1, args.concurrency)) as ex, open(args.out, "w", encoding="utf-8") as fout:
        futures = [ex.submit(job, i) for i in range(args.n)]
        for fut in as_completed(futures):
            rec = fut.result()
            with lock:
                fout.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"Wrote {args.n} runs to {args.out}")


if __name__ == "__main__":
    main()


