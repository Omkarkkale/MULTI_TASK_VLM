from pathlib import Path
import csv


DATASET_ROOT = Path("/workspace/extracted/crusher_dataset_v2")
MASTER_METADATA = DATASET_ROOT / "master_metadata_clean.csv"

SPLIT_DIR = DATASET_ROOT / "splits"

TRAIN_FILE = SPLIT_DIR / "train_metadata.csv"
VAL_FILE = SPLIT_DIR / "val_metadata.csv"
TEST_FILE = SPLIT_DIR / "test_metadata.csv"


TRAIN_RECORDINGS = {"41", "75", "94", "120", "137"}
VAL_RECORDINGS = {"40"}
TEST_RECORDINGS = {"39", "118"}


def main():

    if not MASTER_METADATA.exists():
        print(f"ERROR: {MASTER_METADATA} not found.")
        return

    SPLIT_DIR.mkdir(parents=True, exist_ok=True)

    with open(MASTER_METADATA, newline="") as f:
        rows = list(csv.DictReader(f))

    train_rows = []
    val_rows = []
    test_rows = []
    unassigned_rows = []

    for row in rows:

        recording_id = str(row["recording_id"])

        if recording_id in TRAIN_RECORDINGS:
            train_rows.append(row)

        elif recording_id in VAL_RECORDINGS:
            val_rows.append(row)

        elif recording_id in TEST_RECORDINGS:
            test_rows.append(row)

        else:
            unassigned_rows.append(row)

    fieldnames = rows[0].keys()

    def write_csv(path, split_rows):

        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=fieldnames
            )

            writer.writeheader()
            writer.writerows(split_rows)

    write_csv(TRAIN_FILE, train_rows)
    write_csv(VAL_FILE, val_rows)
    write_csv(TEST_FILE, test_rows)

    print("=" * 70)
    print("FINAL RECORDING-LEVEL SPLITS CREATED")
    print("=" * 70)

    print(
        f"TRAIN recordings: "
        f"{sorted(TRAIN_RECORDINGS, key=int)}"
    )
    print(
        f"VAL recordings:   "
        f"{sorted(VAL_RECORDINGS, key=int)}"
    )
    print(
        f"TEST recordings:  "
        f"{sorted(TEST_RECORDINGS, key=int)}"
    )

    print()

    total = len(rows)

    print(
        f"Train samples: {len(train_rows):4d} "
        f"({100 * len(train_rows) / total:5.1f}%)"
    )

    print(
        f"Val samples:   {len(val_rows):4d} "
        f"({100 * len(val_rows) / total:5.1f}%)"
    )

    print(
        f"Test samples:  {len(test_rows):4d} "
        f"({100 * len(test_rows) / total:5.1f}%)"
    )

    print(
        f"Total samples: {total:4d}"
    )

    print()

    if unassigned_rows:
        print(
            f"WARNING: {len(unassigned_rows)} "
            f"samples were not assigned!"
        )
    else:
        print("All samples assigned exactly once.")

    # Safety check: no recording overlap
    assert TRAIN_RECORDINGS.isdisjoint(VAL_RECORDINGS)
    assert TRAIN_RECORDINGS.isdisjoint(TEST_RECORDINGS)
    assert VAL_RECORDINGS.isdisjoint(TEST_RECORDINGS)

    # Safety check: counts
    assert (
        len(train_rows)
        + len(val_rows)
        + len(test_rows)
        == total
    )

    print()
    print("Files created:")
    print(TRAIN_FILE)
    print(VAL_FILE)
    print(TEST_FILE)


if __name__ == "__main__":
    main()