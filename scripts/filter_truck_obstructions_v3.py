from pathlib import Path
import csv

DATASET_ROOT = Path("/workspace/extracted/crusher_dataset_v3")

MASTER_METADATA = DATASET_ROOT / "master_metadata.csv"
CLEAN_METADATA = DATASET_ROOT / "master_metadata_clean.csv"
REJECTED_CSV = DATASET_ROOT / "rejected_samples.csv"

# ============================================================
# RECORDING-LEVEL REJECTIONS
# ============================================================

# Recording 121 was visually inspected and the truck obstructs
# the relevant crusher view throughout the recording.
REJECTED_RECORDINGS = {
    "121": "truck_obstruction_entire_recording",
    "384": "truck_obstruction_entire_recording",
}

# ============================================================
# SAMPLE-LEVEL REJECTIONS
# ============================================================

# Previously visually confirmed truck obstruction samples.
REJECTED_SAMPLES = {
    ("94", 57): "truck_obstruction",
    ("94", 58): "truck_obstruction",
    ("94", 59): "truck_obstruction",
    ("94", 60): "truck_obstruction",
    ("94", 61): "truck_obstruction",

    ("118", 104): "truck_obstruction",
    ("118", 105): "truck_obstruction",
    ("118", 106): "truck_obstruction",
    ("118", 107): "truck_obstruction",
    ("118", 108): "truck_obstruction",
    ("118", 109): "truck_obstruction",
    ("118", 110): "truck_obstruction",
    ("118", 111): "truck_obstruction",
    ("118", 112): "truck_obstruction",
    ("118", 113): "truck_obstruction",

    # V3 recording-overview QC
    ("142", 24): "truck_obstruction",
    ("142", 27): "truck_obstruction",
    ("142", 31): "truck_obstruction",
    ("142", 34): "truck_obstruction",
    ("142", 38): "truck_obstruction",

    ("145", 296): "truck_obstruction",

    ("215", 73): "truck_obstruction",
    ("215", 82): "truck_obstruction",
    ("215", 91): "truck_obstruction",
    ("215", 101): "truck_obstruction",

    ("217", 74): "truck_obstruction",

    ("309", 20): "truck_obstruction",
    ("309", 25): "truck_obstruction",
    ("309", 29): "truck_obstruction",

    ("479", 62): "truck_obstruction",
}


def main():
    if not MASTER_METADATA.exists():
        print(f"ERROR: {MASTER_METADATA} not found.")
        return

    with open(MASTER_METADATA, newline="") as f:
        rows = list(csv.DictReader(f))

    clean_rows = []
    rejected_rows = []

    recording_rejection_count = 0
    sample_rejection_count = 0

    for row in rows:
        recording_id = str(row["recording_id"])
        sample = int(row["sample"])

        reason = None
        rejection_type = None

        # Entire-recording rejection
        if recording_id in REJECTED_RECORDINGS:
            reason = REJECTED_RECORDINGS[recording_id]
            rejection_type = "recording_level"
            recording_rejection_count += 1

        # Individual-sample rejection
        elif (recording_id, sample) in REJECTED_SAMPLES:
            reason = REJECTED_SAMPLES[(recording_id, sample)]
            rejection_type = "sample_level"
            sample_rejection_count += 1

        if reason is not None:
            rejected_rows.append(
                {
                    "recording_id": recording_id,
                    "sample": sample,
                    "fill_level": row["fill_level"],
                    "front_narrow": row["front_narrow"],
                    "front_wide": row["front_wide"],
                    "rejection_type": rejection_type,
                    "reason": reason,
                }
            )
        else:
            clean_rows.append(row)

    # --------------------------------------------------------
    # Save clean metadata
    # --------------------------------------------------------
    with open(CLEAN_METADATA, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=rows[0].keys()
        )
        writer.writeheader()
        writer.writerows(clean_rows)

    # --------------------------------------------------------
    # Save rejected-sample audit log
    # --------------------------------------------------------
    rejected_fieldnames = [
        "recording_id",
        "sample",
        "fill_level",
        "front_narrow",
        "front_wide",
        "rejection_type",
        "reason",
    ]

    with open(REJECTED_CSV, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=rejected_fieldnames
        )
        writer.writeheader()
        writer.writerows(rejected_rows)

    # --------------------------------------------------------
    # Report
    # --------------------------------------------------------
    print("=" * 70)
    print("V3 VISUAL QC FILTER COMPLETE")
    print("=" * 70)

    print(f"Original synchronized samples : {len(rows)}")
    print(f"Recording-level rejected      : {recording_rejection_count}")
    print(f"Sample-level rejected         : {sample_rejection_count}")
    print(f"Total rejected                : {len(rejected_rows)}")
    print(f"Final visually clean samples     : {len(clean_rows)}")

    print("\nRejected recordings:")
    for rid, reason in REJECTED_RECORDINGS.items():
        count = sum(
            1 for r in rejected_rows
            if r["recording_id"] == rid
            and r["rejection_type"] == "recording_level"
        )
        print(
            f"  REC {rid}: {count} samples "
            f"({reason})"
        )

    print("\nSample-level rejected:")
    for r in rejected_rows:
        if r["rejection_type"] != "sample_level":
            continue
        print(
            f"  REC {r['recording_id']} "
            f"Sample {int(r['sample']):04d} "
            f"Fill {r['fill_level']}% "
            f"Reason: {r['reason']}"
        )

    print("\nClean metadata:")
    print(CLEAN_METADATA)

    print("\nRejected audit log:")
    print(REJECTED_CSV)

    print("\nNOTE:")
    print(
        "No images or original master metadata were deleted or modified."
    )



# ============================================================
# ADDITIONAL FULL MANUAL CONTACT-SHEET QC
# ============================================================

FULL_MANUAL_QC_REJECTIONS = {
    # REC 142
    ("142", 25), ("142", 26), ("142", 28), ("142", 29),
    ("142", 32), ("142", 33), ("142", 35), ("142", 36),
    ("142", 37),

    # REC 145
    ("145", 287), ("145", 288), ("145", 289), ("145", 290),
    ("145", 291), ("145", 292), ("145", 293), ("145", 294),
    ("145", 295),

    # REC 208
    ("208", 1), ("208", 2), ("208", 3), ("208", 4),
    ("208", 5), ("208", 6), ("208", 7), ("208", 8),
    ("208", 9), ("208", 10), ("208", 11), ("208", 12),

    # REC 215
    ("215", 6), ("215", 12),
    ("215", 37), ("215", 41), ("215", 44), ("215", 47),
    ("215", 60), ("215", 72),
    ("215", 74), ("215", 75), ("215", 76), ("215", 77),
    ("215", 78), ("215", 79), ("215", 80), ("215", 81),
    ("215", 83), ("215", 84), ("215", 85), ("215", 86),
    ("215", 87), ("215", 88), ("215", 89), ("215", 90),
    ("215", 92), ("215", 93), ("215", 94), ("215", 95),
    ("215", 96), ("215", 97), ("215", 98), ("215", 99),
    ("215", 100),

    # REC 217
    ("217", 52), ("217", 55), ("217", 63), ("217", 67),
    ("217", 71), ("217", 77), ("217", 80),

    # REC 309
    ("309", 19), ("309", 21), ("309", 22), ("309", 23),
    ("309", 24), ("309", 26), ("309", 27), ("309", 28),
    ("309", 30), ("309", 31),

    # REC 479
    ("479", 65),
}

for key in FULL_MANUAL_QC_REJECTIONS:
    REJECTED_SAMPLES[key] = "truck_obstruction"


if __name__ == "__main__":
    main()
