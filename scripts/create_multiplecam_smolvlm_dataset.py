from pathlib import Path
import csv
import json

DATASET_DIR = Path(
    "/workspace/extracted/crusher_dataset_multicam"
)

METADATA_PATH = DATASET_DIR / "metadata.csv"

OUTPUT_PATH = (
    DATASET_DIR / "smolvlm_multicam_dataset.jsonl"
)

PROMPT = "What is the crusher fill level?"


with open(METADATA_PATH, newline="") as f:
    rows = list(csv.DictReader(f))


with open(OUTPUT_PATH, "w") as outfile:

    for row in rows:

        fill_level = float(row["fill_level"])

        # Avoid answers like "25.0%"
        if fill_level.is_integer():
            answer = f"{int(fill_level)}%"
        else:
            answer = f"{fill_level}%"

        sample = {
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
                        },
                    ],
                },
                {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "text",
                            "text": answer
                        }
                    ],
                },
            ],

            "metadata": {
                "sample": int(row["sample"]),
                "fill_level": fill_level,

                "narrow_delta_t_seconds": float(
                    row["narrow_delta_t_seconds"]
                ),

                "wide_delta_t_seconds": float(
                    row["wide_delta_t_seconds"]
                ),
            },
        }

        outfile.write(
            json.dumps(sample) + "\n"
        )


print("Conversion complete.")
print(f"Total samples: {len(rows)}")
print(f"Output: {OUTPUT_PATH}")