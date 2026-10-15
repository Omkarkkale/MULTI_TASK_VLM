#!/usr/bin/env python3
"""Read-only validation and summary for a clean crusher metadata CSV."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from crusher_dataset import load_examples


def fill_bin(value: float) -> str:
    lower = min(int(value // 10) * 10, 90)
    return f"{lower:02d}-{lower + 10:03d}"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_source_roots(path: Path | None) -> dict[str, Path] | None:
    if path is None:
        return None
    raw_mapping = json.loads(path.read_text())
    if not isinstance(raw_mapping, dict):
        raise ValueError(f"Source-root map must be a JSON object: {path}")
    return {
        str(name): (path.parent / str(root)).resolve()
        for name, root in raw_mapping.items()
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata-csv", type=Path, required=True)
    parser.add_argument("--image-root", type=Path, required=True)
    parser.add_argument(
        "--source-roots-json",
        type=Path,
        help="Optional source_dataset-to-image-root map for a combined release such as v4.",
    )
    parser.add_argument(
        "--manifest-output",
        type=Path,
        help="Optional path for a JSON summary. Omit for a strictly read-only check.",
    )
    args = parser.parse_args()

    source_roots = load_source_roots(args.source_roots_json)
    examples = load_examples(args.metadata_csv, args.image_root, source_roots)
    recording_counts = Counter(example.recording_id for example in examples)
    bin_counts = Counter(fill_bin(example.fill_level) for example in examples)
    manifest = {
        "metadata_csv": str(args.metadata_csv.resolve()),
        "metadata_sha256": sha256(args.metadata_csv),
        "image_root": str(args.image_root.resolve()),
        "source_roots_json": (
            str(args.source_roots_json.resolve()) if args.source_roots_json else None
        ),
        "row_count": len(examples),
        "recording_count": len(recording_counts),
        "recording_ids": sorted(recording_counts, key=lambda value: int(value)),
        "samples_per_recording": dict(
            sorted(recording_counts.items(), key=lambda item: int(item[0]))
        ),
        "fill_level_bins": dict(sorted(bin_counts.items())),
        "status": "preflight_passed",
    }

    print(json.dumps(manifest, indent=2))
    if args.manifest_output:
        args.manifest_output.parent.mkdir(parents=True, exist_ok=True)
        args.manifest_output.write_text(json.dumps(manifest, indent=2) + "\n")
        print(f"Wrote manifest: {args.manifest_output}")


if __name__ == "__main__":
    main()
