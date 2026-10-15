#!/usr/bin/env python3
"""Evaluate a prediction CSV and retain failure/coverage information."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


def fill_bin(value: float) -> str:
    lower = min(int(value // 10) * 10, 90)
    return f"{lower:02d}-{lower + 10:03d}"


def mae(rows: list[dict[str, float]]) -> float | None:
    return None if not rows else sum(abs(row["prediction"] - row["true"]) for row in rows) / len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    with args.predictions.open(newline="") as handle:
        input_rows = list(csv.DictReader(handle))

    valid: list[dict[str, float | str]] = []
    invalid = 0
    for row in input_rows:
        try:
            true = float(row["true_fill_level"])
            prediction = float(row["prediction"])
            if row.get("status", "valid") != "valid" or not 0 <= prediction <= 100:
                raise ValueError
            valid.append({"true": true, "prediction": prediction, "recording_id": row["recording_id"]})
        except (KeyError, TypeError, ValueError):
            invalid += 1

    by_recording: dict[str, list[dict[str, float | str]]] = defaultdict(list)
    by_bin: dict[str, list[dict[str, float | str]]] = defaultdict(list)
    for row in valid:
        by_recording[str(row["recording_id"])].append(row)
        by_bin[fill_bin(float(row["true"]))].append(row)

    report = {
        "total_examples": len(input_rows),
        "valid_predictions": len(valid),
        "invalid_predictions": invalid,
        "valid_prediction_rate": len(valid) / len(input_rows) if input_rows else 0.0,
        "mae_percentage_points_valid_only": mae(valid),
        "mae_by_recording": {key: mae(value) for key, value in sorted(by_recording.items())},
        "mae_by_true_fill_bin": {key: mae(value) for key, value in sorted(by_bin.items())},
        "NOTE": "Invalid-output policy must be approved before final reporting.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    print(f"Wrote report: {args.output}")


if __name__ == "__main__":
    main()
