
HARD_QN = """
Let $\triangle$$ABC$ have incenter $I$, circumcenter $O$, inradius $6$, and circumradius $13$. Suppose that $\overline{IA} \perp \overline{OI}$. Find $AB \cdot AC$.
"""

EASY_QN = """
Let $ABCDEF$ be a convex equilateral hexagon in which all pairs of opposite sides are parallel. The triangle whose sides are extensions of segments $AB$, $CD$, and $EF$ has side lengths $200$, $240$, and $300$. Find the side length of the hexagon.
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