from pathlib import Path
import csv
import statistics


DATASET_ROOT = Path("/workspace/extracted/crusher_dataset_v2")
METADATA = DATASET_ROOT / "master_metadata_clean.csv"


SPLITS = {
    "TRAIN": {"39", "41", "75", "118", "137"},
    "VAL": {"40"},
    "TEST": {"94", "120"},
}


def summarize(name, rows):

    values = [float(r["fill_level"]) for r in rows]

    bins = [
        (0, 20),
        (20, 40),
        (40, 60),
        (60, 80),
        (80, 101),
    ]

    counts = [
        sum(low <= v < high for v in values)
        for low, high in bins
    ]

    print(f"\n{name}")
    print("-" * 50)

    print(f"Samples : {len(values)}")
    print(f"Min     : {min(values):.1f}%")
    print(f"Max     : {max(values):.1f}%")
    print(f"Mean    : {statistics.mean(values):.1f}%")
    print(f"Median  : {statistics.median(values):.1f}%")
    print(f"Std     : {statistics.pstdev(values):.1f}")

    print("\nCoverage:")

    labels = [
        "0-19",
        "20-39",
        "40-59",
        "60-79",
        "80-100",
    ]

    for label, count in zip(labels, counts):

        percentage = 100 * count / len(values)

        print(
            f"{label:>6}% : "
            f"{count:>4} "
            f"({percentage:5.1f}%)"
        )


def main():

    with open(METADATA, newline="") as f:
        rows = list(csv.DictReader(f))

    print("=" * 60)
    print("PROPOSED RECORDING-LEVEL SPLIT")
    print("=" * 60)

    total_assigned = 0

    for split_name, recording_ids in SPLITS.items():

        split_rows = [
            row for row in rows
            if row["recording_id"] in recording_ids
        ]

        total_assigned += len(split_rows)

        print(
            f"\nRecordings for {split_name}: "
            f"{sorted(recording_ids, key=int)}"
        )

        summarize(split_name, split_rows)

    print("\n" + "=" * 60)
    print(f"Total metadata samples : {len(rows)}")
    print(f"Total assigned samples : {total_assigned}")

    if total_assigned == len(rows):
        print("All samples assigned exactly once.")
    else:
        print("WARNING: split assignment mismatch!")


if __name__ == "__main__":
    main()