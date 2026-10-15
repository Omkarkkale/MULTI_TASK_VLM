#!/usr/bin/env python3
"""Write predictions for the honest mean-value baseline."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-csv", type=Path, required=True)
    parser.add_argument("--eval-csv", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    train_rows = read_rows(args.train_csv)
    eval_rows = read_rows(args.eval_csv)
    if not train_rows:
        raise ValueError("Training CSV is empty.")

    mean_fill = sum(float(row["fill_level"]) for row in train_rows) / len(train_rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="") as handle:
        fields = ["recording_id", "sample", "true_fill_level", "prediction", "status", "raw_output"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in eval_rows:
            writer.writerow({
                "recording_id": row["recording_id"],
                "sample": row["sample"],
                "true_fill_level": row["fill_level"],
                "prediction": f"{mean_fill:.6f}",
                "status": "valid",
                "raw_output": "training_set_mean",
            })
    print(f"Training-set mean: {mean_fill:.4f}")
    print(f"Wrote {len(eval_rows)} predictions: {args.output}")


if __name__ == "__main__":
    main()
