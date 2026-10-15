#!/usr/bin/env python3
"""Create leakage-safe metadata splits from an explicit recording assignment."""

from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import yaml


VALID_SPLITS = {"train", "val", "test"}


def load_config(path: Path) -> dict[str, Any]:
    with path.open() as handle:
        return yaml.safe_load(handle)


def require_real_path(value: str, field: str) -> Path:
    if not value or value.startswith("CONFIRM_WITH_BJARNE"):
        raise ValueError(f"Set dataset.{field} in the config after the review.")
    return Path(value)


def load_assignments(path: Path) -> dict[str, str]:
    assignments: dict[str, str] = {}
    with path.open(newline="") as handle:
        for row in csv.DictReader(handle):
            recording_id = (row.get("recording_id") or "").strip()
            split = (row.get("split") or "").strip().lower()
            if not recording_id or recording_id.startswith("#"):
                continue
            if split not in VALID_SPLITS:
                raise ValueError(
                    f"Recording {recording_id!r} has invalid split {split!r}. "
                    f"Use one of: {sorted(VALID_SPLITS)}."
                )
            if recording_id in assignments:
                raise ValueError(f"Duplicate recording assignment: {recording_id}")
            assignments[recording_id] = split
    if not assignments:
        raise ValueError("No recording assignments found.")
    return assignments


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--assignments", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    config = load_config(args.config)
    root = require_real_path(config["dataset"]["root"], "root")
    metadata = require_real_path(config["dataset"]["metadata_csv"], "metadata_csv")
    metadata = metadata if metadata.is_absolute() else root / metadata
    if not metadata.is_file():
        raise FileNotFoundError(f"Metadata CSV not found: {metadata}")

    assignments = load_assignments(args.assignments)
    with metadata.open(newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fieldnames = reader.fieldnames

    if not rows or not fieldnames:
        raise ValueError("Metadata CSV has no data rows.")
    missing_columns = set(config["dataset"]["required_columns"]) - set(fieldnames)
    if missing_columns:
        raise ValueError(f"Metadata lacks required columns: {sorted(missing_columns)}")

    recordings_in_data = {str(row["recording_id"]) for row in rows}
    missing_assignments = recordings_in_data - set(assignments)
    unknown_assignments = set(assignments) - recordings_in_data
    if missing_assignments or unknown_assignments:
        problems = []
        if missing_assignments:
            problems.append(f"unassigned recordings: {sorted(missing_assignments)}")
        if unknown_assignments:
            problems.append(f"unknown recordings: {sorted(unknown_assignments)}")
        raise ValueError("; ".join(problems))

    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[assignments[str(row["recording_id"])]].append(row)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for split in sorted(VALID_SPLITS):
        output = args.output_dir / f"{split}_metadata.csv"
        with output.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(grouped[split])
        print(f"{split:5} {len(grouped[split]):6} rows  -> {output}")

    counts = Counter(assignments.values())
    print("Recordings:", dict(sorted(counts.items())))
    print("Split creation complete. Keep this assignment CSV immutable for final runs.")


if __name__ == "__main__":
    main()
