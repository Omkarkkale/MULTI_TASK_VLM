"""Dataset utilities for two-view crusher fill-level experiments.

This module deliberately does not choose a train/validation/test split.  It
only turns an already selected metadata CSV into examples with two RGB images
and a numeric fill-level target.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping


REQUIRED_COLUMNS = {
    "recording_id",
    "sample",
    "front_narrow",
    "front_wide",
    "fill_level",
}


@dataclass(frozen=True)
class CrusherExample:
    """One clean crusher label and its two synchronized camera images."""

    recording_id: str
    sample_id: str
    source_dataset: str | None
    narrow_path: Path
    wide_path: Path
    fill_level: float


def load_examples(
    metadata_csv: Path,
    image_root: Path,
    source_roots: Mapping[str, Path] | None = None,
) -> list[CrusherExample]:
    """Read examples and validate only their metadata schema and image paths."""

    with metadata_csv.open(newline="") as handle:
        reader = csv.DictReader(handle)
        columns = set(reader.fieldnames or [])
        missing = REQUIRED_COLUMNS - columns
        if missing:
            raise ValueError(
                f"{metadata_csv} is missing required columns: {sorted(missing)}"
            )
        rows = list(reader)

    examples: list[CrusherExample] = []
    for line_number, row in enumerate(rows, start=2):
        try:
            fill_level = float(row["fill_level"])
        except (TypeError, ValueError) as error:
            raise ValueError(
                f"Invalid fill_level at {metadata_csv}:{line_number}: "
                f"{row.get('fill_level')!r}"
            ) from error
        if not 0 <= fill_level <= 100:
            raise ValueError(
                f"Fill level outside 0–100 at {metadata_csv}:{line_number}: {fill_level}"
            )

        row_root = image_root
        if "source_dataset" in row:
            source_name = row["source_dataset"]
            if source_roots is None or source_name not in source_roots:
                raise ValueError(
                    f"{metadata_csv}:{line_number} has source_dataset={source_name!r}, "
                    "but no matching source root was supplied."
                )
            row_root = source_roots[source_name]

        narrow_path = row_root / row["front_narrow"]
        wide_path = row_root / row["front_wide"]
        missing_paths = [path for path in (narrow_path, wide_path) if not path.is_file()]
        if missing_paths:
            raise FileNotFoundError(
                f"Missing image(s) at {metadata_csv}:{line_number}: "
                + ", ".join(str(path) for path in missing_paths)
            )
        examples.append(
            CrusherExample(
                recording_id=str(row["recording_id"]),
                sample_id=str(row["sample"]),
                source_dataset=row.get("source_dataset") or None,
                narrow_path=narrow_path,
                wide_path=wide_path,
                fill_level=fill_level,
            )
        )
    return examples


class TwoViewCrusherDataset:
    """PyTorch-compatible dataset that loads both camera images as RGB PIL images.

    The Qwen-specific data collator will later turn these PIL images and a
    fixed prompt into processor inputs.  Keeping this class model-independent
    makes it usable for the mean baseline, zero-shot model, and QLoRA model.
    """

    def __init__(self, examples: Iterable[CrusherExample]):
        self.examples = list(examples)

    def __len__(self) -> int:
        return len(self.examples)

    def __getitem__(self, index: int) -> dict[str, object]:
        # Import lazily: inspecting metadata must not require Pillow/Torch.
        try:
            from PIL import Image
        except ModuleNotFoundError as error:
            raise RuntimeError(
                "Loading image pixels requires Pillow. Install the pinned "
                "training/requirements.txt dependencies in the project venv."
            ) from error

        example = self.examples[index]
        with Image.open(example.narrow_path) as narrow_file:
            narrow = narrow_file.convert("RGB").copy()
        with Image.open(example.wide_path) as wide_file:
            wide = wide_file.convert("RGB").copy()
        return {
            "images": [narrow, wide],
            "fill_level": example.fill_level,
            "recording_id": example.recording_id,
            "sample_id": example.sample_id,
            "source_dataset": example.source_dataset,
            "image_paths": [str(example.narrow_path), str(example.wide_path)],
        }
