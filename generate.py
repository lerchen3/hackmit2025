
QN = """
Find the sum of all positive integers $n$ such that when $1^3+2^3+3^3+\cdots +n^3$ is divided by $n+5$, the remainder is $17$.
"""

if __name__ == "__main__":
    import os
    from apimanager import APIManager

    api = APIManager()

    questions = [
        ("EASY", EASY_QN),
        ("MEDIUM", MEDIUM_QN),
        ("HARD", HARD_QN),
    ]

    # Model selection
    model = "gpt-5-nano"
    supports_stream = not model.startswith("gpt-5")
    supports_usage = not model.startswith("gpt-5")

    for label, q in questions:
        payload = {
            "provider": "openai",
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a helpful math problem solver. Provide reasoning briefly and a final numeric answer."},
                {"role": "user", "content": q.strip()},
            ],
        }
        if supports_usage:
            payload["debug_tokens"] = True

        print(f"\n--- {label} ---")
        if supports_stream:
            printed_any = False
            for piece in api.stream(payload):
                print(piece, end="", flush=True)
                printed_any = True
            print()
            if not printed_any:
                print("[error] No content streamed. Check OPENAI_API_KEY and model.")
        else:
            text = api.query(payload)
            if text is None:
                print("[error] No content returned. Check OPENAI_API_KEY and model.")
            else:
                print(text)

        if supports_usage:
            counts = api.get_last_token_counts()
            if counts is not None:
                print(f"[OPENAI] tokens prompt={counts['prompt']} completion={counts['completion']} total={counts['total']}")