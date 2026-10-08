from pathlib import Path
import csv


DATASET_ROOT = Path("/workspace/extracted/crusher_dataset_v2")

MASTER_METADATA = DATASET_ROOT / "master_metadata.csv"
CLEAN_METADATA = DATASET_ROOT / "master_metadata_clean.csv"
REJECTED_CSV = DATASET_ROOT / "rejected_samples.csv"


# Manual QC rejection list
REJECTED_SAMPLES = {
    ("94", 57),
    ("94", 58),
    ("94", 59),
    ("94", 60),
    ("94", 61),

    ("118", 104),
    ("118", 105),
    ("118", 106),
    ("118", 107),
    ("118", 108),
    ("118", 109),
    ("118", 110),
    ("118", 111),
    ("118", 112),
    ("118", 113),
}


def main():
    if not MASTER_METADATA.exists():
        print(f"ERROR: {MASTER_METADATA} not found.")
        return

    with open(MASTER_METADATA, newline="") as f:
        rows = list(csv.DictReader(f))

    clean_rows = []
    rejected_rows = []

    for row in rows:
        recording_id = str(row["recording_id"])
        sample = int(row["sample"])

        key = (recording_id, sample)

        if key in REJECTED_SAMPLES:
            rejected_rows.append(
                {
                    "recording_id": recording_id,
                    "sample": sample,
                    "fill_level": row["fill_level"],
                    "front_narrow": row["front_narrow"],
                    "front_wide": row["front_wide"],
                    "reason": "truck_obstruction",
                }
            )
        else:
            clean_rows.append(row)

    # Save clean metadata
    with open(CLEAN_METADATA, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=rows[0].keys()
        )
        writer.writeheader()
        writer.writerows(clean_rows)

    # Save rejected sample log
    rejected_fieldnames = [
        "recording_id",
        "sample",
        "fill_level",
        "front_narrow",
        "front_wide",
        "reason",
    ]

    with open(REJECTED_CSV, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=rejected_fieldnames
        )
        writer.writeheader()
        writer.writerows(rejected_rows)

    print("=" * 60)
    print("VISUAL QC FILTER COMPLETE")
    print("=" * 60)
    print(f"Original synchronized samples: {len(rows)}")
    print(f"Rejected samples:              {len(rejected_rows)}")
    print(f"Clean samples:                 {len(clean_rows)}")
    print()
    print(f"Clean metadata:")
    print(CLEAN_METADATA)
    print()
    print(f"Rejected sample log:")
    print(REJECTED_CSV)

    print("\nRejected samples:")

    for r in rejected_rows:
        print(
            f"  Recording {r['recording_id']} "
            f"Sample {int(r['sample']):04d} "
            f"Fill {r['fill_level']}% "
            f"Reason: {r['reason']}"
        )


if __name__ == "__main__":
    main()