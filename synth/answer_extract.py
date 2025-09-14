import argparse
import csv
import os
from typing import Optional, List


def extract_last_boxed(latex_text: str) -> Optional[str]:
    """
    Extract the text inside the LAST occurrence of \boxed{...} in the provided
    LaTeX string. Handles nested braces within the \boxed{...} content.

    Returns the inner text without the surrounding braces, or None if not found.
    """
    if not latex_text:
        return None

    search_token = "\\boxed{"  # literal backslash + boxed + opening brace
    last_extracted: Optional[str] = None
    i = 0
    n = len(latex_text)

    while i < n:
        start = latex_text.find(search_token, i)
        if start == -1:
            break
        # Position after the opening brace
        j = start + len(search_token)
        brace_depth = 1
        # Walk forward to find the matching closing brace
        k = j
        while k < n and brace_depth > 0:
            ch = latex_text[k]
            if ch == '{':
                brace_depth += 1
            elif ch == '}':
                brace_depth -= 1
            k += 1

        if brace_depth == 0:
            # k is positioned one past the matching '}'
            content = latex_text[j : k - 1]
            last_extracted = content.strip()
            # Continue searching after this \boxed{...}
            i = k
        else:
            # Unbalanced braces; stop scanning to avoid infinite loop
            break

    return last_extracted


def compute_default_out_path(input_path: str) -> str:
    base_dir, filename = os.path.split(os.path.abspath(input_path))
    name, _ = os.path.splitext(filename)
    # Make it explicit that this CSV has answers extracted into Is_Correct column
    return os.path.join(base_dir, f"{name}.answers.csv")


def process_csv(inp: str, out: str) -> int:
    """Read input CSV, replace Is_Correct with last \boxed{...} from Solution, write output CSV.

    Returns the number of rows written.
    """
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)

    with open(inp, "r", encoding="utf-8", newline="") as fin:
        reader = csv.DictReader(fin)
        fieldnames_in: List[str] = reader.fieldnames or []

        # Ensure we have expected columns; we will preserve all columns but overwrite Is_Correct
        fieldnames_out: List[str] = list(fieldnames_in)
        if "Is_Correct" not in fieldnames_out:
            fieldnames_out.append("Is_Correct")

        with open(out, "w", encoding="utf-8", newline="") as fout:
            writer = csv.DictWriter(fout, fieldnames=fieldnames_out, extrasaction="ignore")
            writer.writeheader()
            row_count = 0
            for row in reader:
                solution_text = row.get("Solution", "")
                extracted = extract_last_boxed(solution_text) or ""
                if(extracted != ""):
                    row["Final_Answer"] = extracted
                    writer.writerow(row)
                    row_count += 1

    return row_count


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Extract the last \\boxed{...} from each Solution and write a new CSV "
            "with the Is_Correct column replaced by the extracted text."
        )
    )
    parser.add_argument(
        "--in",
        dest="inp",
        default=os.path.abspath("/home/ubuntu/hackmit2025/synth/synthetic.csv"),
        help="Input CSV path (default: synth/synthetic.csv)",
    )
    parser.add_argument(
        "--out",
        dest="out",
        default=None,
        help="Output CSV path (default: <input_stem>.answers.csv alongside input)",
    )
    args = parser.parse_args()

    inp = os.path.abspath(args.inp)
    out = os.path.abspath(args.out) if args.out else compute_default_out_path(inp)

    if not os.path.exists(inp):
        print(f"Input file not found: {inp}")
        return

    rows = process_csv(inp, out)
    print(f"Wrote {rows} rows to {out}")


if __name__ == "__main__":
    main()
