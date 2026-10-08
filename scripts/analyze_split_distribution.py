from pathlib import Path
import json
import statistics


DATASET_DIR = Path(
    "/workspace/extracted/crusher_dataset_multicam/splits"
)


splits = {
    "TRAIN": DATASET_DIR / "train.jsonl",
    "VALIDATION": DATASET_DIR / "validation.jsonl",
    "TEST": DATASET_DIR / "test.jsonl",
}


def load_fill_levels(path):

    values = []

    with open(path, "r") as f:
        for line in f:

            sample = json.loads(line)

            fill_level = float(
                sample["metadata"]["fill_level"]
            )

            values.append(fill_level)

    return values


for split_name, path in splits.items():

    values = load_fill_levels(path)

    print()
    print(f"{split_name}")
    print("--------------------------------")

    print(f"Samples: {len(values)}")
    print(f"Min:     {min(values):.1f}%")
    print(f"Max:     {max(values):.1f}%")
    print(f"Mean:    {statistics.mean(values):.2f}%")
    print(f"Median:  {statistics.median(values):.2f}%")
    print(f"Std Dev: {statistics.pstdev(values):.2f}")

    print(
        "Values:",
        ", ".join(
            f"{value:.0f}"
            for value in values
        )
    )