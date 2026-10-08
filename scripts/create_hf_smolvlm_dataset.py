from pathlib import Path
import csv
import json


DATASET_ROOT = Path("/workspace/extracted/crusher_dataset_v2")

SPLIT_DIR = DATASET_ROOT / "splits"
OUTPUT_DIR = DATASET_ROOT / "hf_dataset"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


PROMPT = (
    "Estimate the fill level of the industrial crusher shown in the two images. "
    "Use visual information from both images. "
    "The fill level is a percentage from 0 to 100, where 0 means completely empty "
    "and 100 means completely full. "
    "Return only the estimated percentage."
)


SPLITS = {
    "train": SPLIT_DIR / "train_metadata.csv",
    "val": SPLIT_DIR / "val_metadata.csv",
    "test": SPLIT_DIR / "test_metadata.csv",
}


def convert_split(split_name, metadata_path):

    output_path = OUTPUT_DIR / f"{split_name}.jsonl"

    if not metadata_path.exists():
        print(f"ERROR: {metadata_path} not found.")
        return 0

    with open(metadata_path, newline="") as f:
        rows = list(csv.DictReader(f))

    written = 0
    missing_images = 0

    with open(output_path, "w") as out_file:

        for row in rows:

            narrow_path = DATASET_ROOT / row["front_narrow"]
            wide_path = DATASET_ROOT / row["front_wide"]

            if not narrow_path.exists():
                print(f"Missing image: {narrow_path}")
                missing_images += 1
                continue

            if not wide_path.exists():
                print(f"Missing image: {wide_path}")
                missing_images += 1
                continue

            fill_level = float(row["fill_level"])

            # Make clean text answer:
            # 63.0 -> "63%"
            # 63.5 -> "63.5%"
            if fill_level.is_integer():
                answer = f"{int(fill_level)}%"
            else:
                answer = f"{fill_level:g}%"

            sample = {
                "recording_id": row["recording_id"],
                "sample_id": int(row["sample"]),

                "images": [
                    row["front_narrow"],
                    row["front_wide"],
                ],

                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image"
                            },
                            {
                                "type": "image"
                            },
                            {
                                "type": "text",
                                "text": PROMPT
                            }
                        ]
                    },
                    {
                        "role": "assistant",
                        "content": [
                            {
                                "type": "text",
                                "text": answer
                            }
                        ]
                    }
                ],

                "fill_level": fill_level
            }

            out_file.write(
                json.dumps(sample) + "\n"
            )

            written += 1

    print(
        f"{split_name.upper():5} "
        f"| metadata={len(rows):4d} "
        f"| written={written:4d} "
        f"| missing={missing_images}"
    )

    print(f"      {output_path}")

    return written


def main():

    print("=" * 70)
    print("CREATE HUGGING FACE / SMOLVLM DATASET")
    print("=" * 70)

    total = 0

    for split_name, metadata_path in SPLITS.items():
        total += convert_split(
            split_name,
            metadata_path
        )

    print()
    print("=" * 70)
    print("CONVERSION COMPLETE")
    print("=" * 70)
    print(f"Total examples written: {total}")

    if total == 1519:
        print("Dataset count matches expected clean dataset: 1519")
    else:
        print("WARNING: expected 1519 examples.")


if __name__ == "__main__":
    main()