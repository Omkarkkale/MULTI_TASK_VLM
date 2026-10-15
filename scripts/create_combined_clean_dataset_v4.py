#!/usr/bin/env python3
"""Create the logical v4 clean release from the two approved clean batches.

No image bytes are copied.  The output metadata adds ``source_dataset`` so a
loader can resolve each row's image paths against the immutable source batch.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
OUTPUT = PROJECT / "extracted" / "crusher_dataset_v4"
SOURCES = {
    "crusher_dataset_v3": PROJECT / "extracted" / "crusher_dataset_v3",
    "new_batches_2026_09_28": PROJECT / "extracted" / "new_batches" / "2026_09_28",
}
METADATA_NAME = "master_metadata_clean.csv"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_source(name: str, root: Path) -> tuple[list[str], list[dict[str, str]]]:
    metadata = root / METADATA_NAME
    if not metadata.is_file():
        raise FileNotFoundError(f"Missing clean metadata for {name}: {metadata}")
    with metadata.open(newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames
        rows = list(reader)
    if not fieldnames:
        raise ValueError(f"No header in {metadata}")
    return fieldnames, rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace only generated v4 metadata/manifest files; never source images.",
    )
    args = parser.parse_args()

    output_paths = [
        OUTPUT / METADATA_NAME,
        OUTPUT / "dataset_manifest.json",
        OUTPUT / "source_roots.json",
        OUTPUT / "README.md",
    ]
    existing = [path for path in output_paths if path.exists()]
    if existing and not args.overwrite:
        raise SystemExit(
            "v4 generated files already exist. Inspect them first, then rerun with "
            f"--overwrite if replacement is intentional: {existing}"
        )

    all_rows: list[dict[str, str]] = []
    expected_fields: list[str] | None = None
    source_manifest: dict[str, dict[str, object]] = {}
    identifiers: set[tuple[str, str, str]] = set()

    for name, root in SOURCES.items():
        fieldnames, rows = read_source(name, root)
        if expected_fields is None:
            expected_fields = fieldnames
        elif fieldnames != expected_fields:
            raise ValueError(
                f"Schema differs for {name}. Expected {expected_fields}, got {fieldnames}"
            )

        required = {"recording_id", "sample", "front_narrow", "front_wide", "fill_level"}
        missing = required - set(fieldnames)
        if missing:
            raise ValueError(f"{name} lacks required columns: {sorted(missing)}")

        for row in rows:
            identifier = (name, row["recording_id"], row["sample"])
            if identifier in identifiers:
                raise ValueError(f"Duplicate source/recording/sample identifier: {identifier}")
            identifiers.add(identifier)
            all_rows.append({"source_dataset": name, **row})

        source_manifest[name] = {
            "metadata_csv": str((root / METADATA_NAME).relative_to(PROJECT)),
            "image_root": str(root.relative_to(PROJECT)),
            "metadata_sha256": sha256(root / METADATA_NAME),
            "row_count": len(rows),
            "recording_ids": sorted({row["recording_id"] for row in rows}, key=int),
        }

    assert expected_fields is not None
    OUTPUT.mkdir(parents=True, exist_ok=True)
    output_fields = ["source_dataset", *expected_fields]
    with (OUTPUT / METADATA_NAME).open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=output_fields)
        writer.writeheader()
        writer.writerows(all_rows)

    source_roots = {
        name: os.path.relpath(root, start=OUTPUT) for name, root in SOURCES.items()
    }
    (OUTPUT / "source_roots.json").write_text(json.dumps(source_roots, indent=2) + "\n")
    manifest = {
        "dataset_id": "crusher_dataset_v4",
        "purpose": "combined_clean_pool_for_pre10k_exploration",
        "image_bytes_copied": False,
        "row_count": len(all_rows),
        "recording_count": len({row["recording_id"] for row in all_rows}),
        "sources": source_manifest,
        "combined_metadata_csv": METADATA_NAME,
    }
    (OUTPUT / "dataset_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (OUTPUT / "README.md").write_text(
        "# Crusher Dataset v4\n\n"
        "Logical combined clean release: `crusher_dataset_v3` plus "
        "`new_batches/2026_09_28`. No images are copied. "
        "`source_roots.json` maps each metadata row to its source image root.\n"
    )

    print(f"Created {OUTPUT}")
    print(f"Rows: {len(all_rows)}")
    print(f"Recordings: {manifest['recording_count']}")
    for name, details in source_manifest.items():
        print(f"  {name}: {details['row_count']} rows")


if __name__ == "__main__":
    main()
