import argparse
import csv
import json
import os
from typing import List, Dict, Any


def read_jsonl(path: str) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                if isinstance(rec, dict):
                    records.append(rec)
            except json.JSONDecodeError:
                # Skip malformed lines but continue processing
                continue
    return records


def determine_fieldnames(records: List[Dict[str, Any]]) -> List[str]:
    # Prefer common known fields first if present
    preferred = ["Solution", "Is_Correct"]
    seen = set()
    fieldnames: List[str] = []

    for p in preferred:
        if any(p in r for r in records):
            fieldnames.append(p)
            seen.add(p)

    # Add any other keys discovered across the dataset, in deterministic order
    others = sorted({k for r in records for k in r.keys() if k not in seen})
    fieldnames.extend(others)
    return fieldnames


def write_csv(records: List[Dict[str, Any]], out_path: str, fieldnames: List[str]) -> None:
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for rec in records:
            writer.writerow(rec)


def main():
    parser = argparse.ArgumentParser(description="Convert a JSONL file to CSV.")
    parser.add_argument(
        "--in",
        dest="inp",
        default=os.path.abspath("/home/ubuntu/hackmit2025/synth/synthetic_hard_solns.suffix.jsonl"),
        help="Input JSONL path (default: dataset in synth/)",
    )
    parser.add_argument(
        "--out",
        dest="out",
        default=os.path.abspath("/home/ubuntu/hackmit2025/synth/synthetic_hard_solns.suffix.csv"),
        help="Output CSV path (default: alongside input)",
    )
    args = parser.parse_args()

    records = read_jsonl(args.inp)
    if not records:
        print("No valid records found; nothing to write.")
        return

    fieldnames = determine_fieldnames(records)
    write_csv(records, args.out, fieldnames)
    print(f"Wrote {len(records)} rows to {args.out} with columns: {', '.join(fieldnames)}")


if __name__ == "__main__":
    main()
