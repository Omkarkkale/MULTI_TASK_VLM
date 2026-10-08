from pathlib import Path
import csv
import re
from mcap.reader import make_reader
from mcap_ros2.decoder import DecoderFactory


DATA_DIR = Path("/workspace/data")
OUTPUT_ROOT = Path(
    "/workspace/extracted/new_batches/2026_09_28"
)

BATCH_ID = "2026_09_28"

BATCH_MANIFEST = Path(
    "/workspace/Documentation/01_Dataset/"
    "new_batch_2026_09_28_domain_classification.csv"
)

EXPECTED_DAY_IDS = {
    45, 50, 98, 112, 139, 140, 141,
    206, 212, 214, 216,
    256, 257, 260, 263, 264,
    280, 305, 308, 378,
    401, 402, 426, 456, 474,
}

EXPECTED_NIGHT_IDS = {
    52, 77, 219, 220, 421, 445, 462,
}

EXPECTED_RECORDING_IDS = (
    EXPECTED_DAY_IDS | EXPECTED_NIGHT_IDS
)

EXPECTED_DAY_COUNT = len(EXPECTED_DAY_IDS)
EXPECTED_NIGHT_COUNT = len(EXPECTED_NIGHT_IDS)

# Input selection uses BATCH_MANIFEST.
# Historical exclusion definitions below are retained but unused.


FILL_TOPIC = "/processing/crusher/fill_level"
NARROW_TOPIC = "/sensor/camera/front_narrow/image_raw/compressed/throttled"
WIDE_TOPIC = "/sensor/camera/front_wide/image_raw/compressed/throttled"

MAX_DELTA_SECONDS = 1.0

# Old tiny recording excluded
EXCLUDED_FILES = {
    # Tiny recording excluded from the established pipeline
    "2026_08_22-13_10_54_eye_0.mcap",

    # Night recordings kept separate from the normal/daylight dataset
    "2026_08_22-13_10_54_eye_37.mcap",
    "2026_08_22-13_10_54_eye_38.mcap",
    "2026_08_22-13_10_54_eye_100.mcap",
    "2026_08_22-13_10_54_eye_101.mcap",
    "2026_08_22-13_10_54_eye_125.mcap",
}


def stamp_to_ns(stamp):
    return stamp.sec * 1_000_000_000 + stamp.nanosec


def nearest_index(target_ns, timestamps):
    return min(
        range(len(timestamps)),
        key=lambda i: abs(timestamps[i] - target_ns)
    )


def recording_id_from_name(filename):
    match = re.search(r"_eye_(\d+)", Path(filename).stem)

    if not match:
        raise ValueError(
            f"Could not extract recording ID from: {filename}"
        )

    return match.group(1)


def should_exclude(path):
    rid = recording_id_from_name(path.name)
    name = path.name.lower()

    if rid == "0":
        return True

    if "night" in name:
        return True

    if "mixed" in name:
        return True

    return False


def read_recording(path):
    fills = []
    narrow = []
    wide = []

    with open(path, "rb") as f:
        reader = make_reader(
            f,
            decoder_factories=[DecoderFactory()]
        )

        for schema, channel, message, ros_msg in reader.iter_decoded_messages():
            topic = channel.topic

            if topic == FILL_TOPIC:
                fills.append(
                    {
                        "timestamp_ns": stamp_to_ns(ros_msg.header.stamp),
                        "fill_level": float(ros_msg.data),
                    }
                )

            elif topic == NARROW_TOPIC:
                narrow.append(
                    {
                        "timestamp_ns": stamp_to_ns(ros_msg.header.stamp),
                        "data": bytes(ros_msg.data),
                        "format": getattr(ros_msg, "format", ""),
                    }
                )

            elif topic == WIDE_TOPIC:
                wide.append(
                    {
                        "timestamp_ns": stamp_to_ns(ros_msg.header.stamp),
                        "data": bytes(ros_msg.data),
                        "format": getattr(ros_msg, "format", ""),
                    }
                )

    return fills, narrow, wide


def process_recording(path):
    recording_id = recording_id_from_name(path.name)

    print(f"\nProcessing recording {recording_id}")
    print(path.name)

    fills, narrow, wide = read_recording(path)

    print(f"  Fill messages:   {len(fills)}")
    print(f"  Narrow frames:   {len(narrow)}")
    print(f"  Wide frames:     {len(wide)}")

    if not fills or not narrow or not wide:
        print("  SKIPPED: missing required topics")
        return []

    recording_dir = OUTPUT_ROOT / recording_id
    narrow_dir = recording_dir / "front_narrow"
    wide_dir = recording_dir / "front_wide"

    narrow_dir.mkdir(parents=True, exist_ok=True)
    wide_dir.mkdir(parents=True, exist_ok=True)

    narrow_timestamps = [x["timestamp_ns"] for x in narrow]
    wide_timestamps = [x["timestamp_ns"] for x in wide]

    rows = []
    valid_count = 0
    rejected_count = 0

    for fill_idx, fill in enumerate(fills, start=1):
        fill_ts = fill["timestamp_ns"]

        n_idx = nearest_index(fill_ts, narrow_timestamps)
        w_idx = nearest_index(fill_ts, wide_timestamps)

        n_ts = narrow[n_idx]["timestamp_ns"]
        w_ts = wide[w_idx]["timestamp_ns"]

        n_signed_delta = (n_ts - fill_ts) / 1e9
        w_signed_delta = (w_ts - fill_ts) / 1e9

        n_abs_delta = abs(n_signed_delta)
        w_abs_delta = abs(w_signed_delta)

        if (
            n_abs_delta > MAX_DELTA_SECONDS
            or w_abs_delta > MAX_DELTA_SECONDS
        ):
            rejected_count += 1
            continue

        valid_count += 1

        sample_name = f"sample_{valid_count:04d}"

        narrow_filename = f"{sample_name}_narrow.jpg"
        wide_filename = f"{sample_name}_wide.jpg"

        narrow_path = narrow_dir / narrow_filename
        wide_path = wide_dir / wide_filename

        # CompressedImage data is already JPEG bytes in these recordings.
        with open(narrow_path, "wb") as f:
            f.write(narrow[n_idx]["data"])

        with open(wide_path, "wb") as f:
            f.write(wide[w_idx]["data"])

        row = {
            "recording_id": recording_id,
            "source_mcap": path.name,
            "sample": valid_count,
            "front_narrow": str(
                Path(recording_id)
                / "front_narrow"
                / narrow_filename
            ),
            "front_wide": str(
                Path(recording_id)
                / "front_wide"
                / wide_filename
            ),
            "fill_level": fill["fill_level"],
            "fill_timestamp_ns": fill_ts,
            "narrow_camera_index": n_idx,
            "narrow_timestamp_ns": n_ts,
            "narrow_delta_t_seconds": n_abs_delta,
            "narrow_signed_delta_t_seconds": n_signed_delta,
            "wide_camera_index": w_idx,
            "wide_timestamp_ns": w_ts,
            "wide_delta_t_seconds": w_abs_delta,
            "wide_signed_delta_t_seconds": w_signed_delta,
        }

        rows.append(row)

    metadata_path = recording_dir / "metadata.csv"

    if rows:
        with open(metadata_path, "w", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=list(rows[0].keys())
            )
            writer.writeheader()
            writer.writerows(rows)

    print(f"  Valid samples:   {valid_count}")
    print(f"  Rejected:        {rejected_count}")
    print(f"  Metadata:        {metadata_path}")

    return rows


def load_batch_mcaps():
    """Validate the batch manifest and select its DAY source files.

    This function performs no output writes and does not decode MCAPs.
    """

    if not DATA_DIR.is_dir():
        raise SystemExit(
            f"STOP: data directory not found: {DATA_DIR}"
        )

    if not BATCH_MANIFEST.is_file():
        raise SystemExit(
            f"STOP: batch manifest not found: {BATCH_MANIFEST}"
        )

    required_fields = {
        "batch_id",
        "recording_id",
        "source_mcap",
        "lighting_domain",
        "lighting_review_method",
        "lighting_review_status",
    }

    with BATCH_MANIFEST.open(
        newline="",
        encoding="utf-8",
    ) as f:
        reader = csv.DictReader(f)

        missing_fields = (
            required_fields - set(reader.fieldnames or [])
        )

        if missing_fields:
            raise SystemExit(
                "STOP: manifest columns missing: "
                + ", ".join(sorted(missing_fields))
            )

        rows = list(reader)

    if len(rows) != len(EXPECTED_RECORDING_IDS):
        raise SystemExit(
            f"STOP: expected {len(EXPECTED_RECORDING_IDS)} "
            f"manifest rows; found {len(rows)}."
        )

    try:
        recording_ids = [
            int(row["recording_id"])
            for row in rows
        ]
    except (TypeError, ValueError) as exc:
        raise SystemExit(
            "STOP: manifest contains an invalid recording ID."
        ) from exc

    if len(set(recording_ids)) != len(recording_ids):
        raise SystemExit(
            "STOP: duplicate recording IDs in manifest."
        )

    if set(recording_ids) != EXPECTED_RECORDING_IDS:
        raise SystemExit(
            "STOP: manifest recording IDs differ from the "
            "confirmed 32-recording batch."
        )

    source_names = [
        row["source_mcap"]
        for row in rows
    ]

    if len(set(source_names)) != len(source_names):
        raise SystemExit(
            "STOP: duplicate source filenames in manifest."
        )

    domain_counts = {"DAY": 0, "NIGHT": 0}
    day_paths = []

    for row in rows:
        rid = int(row["recording_id"])

        if row["batch_id"] != BATCH_ID:
            raise SystemExit(
                f"STOP: unexpected batch ID for REC {rid}."
            )

        if (
            row["lighting_review_method"] != "manual_foxglove"
            or row["lighting_review_status"] != "completed"
        ):
            raise SystemExit(
                f"STOP: REC {rid} lacks completed manual "
                "Foxglove lighting review."
            )

        domain = row["lighting_domain"]

        if domain not in domain_counts:
            raise SystemExit(
                f"STOP: unexpected lighting domain for REC {rid}: "
                f"{domain!r}"
            )

        # Verify exact manually approved DAY/NIGHT identities.
        # Correct totals alone cannot detect a swapped classification.
        expected_domain = (
            "DAY"
            if rid in EXPECTED_DAY_IDS
            else "NIGHT"
        )

        if domain != expected_domain:
            raise SystemExit(
                f"STOP: lighting-domain mismatch for REC {rid}: "
                f"expected {expected_domain}, found {domain!r}."
            )

        domain_counts[domain] += 1

        name = row["source_mcap"]

        if not name or Path(name).name != name:
            raise SystemExit(
                f"STOP: expected a source filename only for REC {rid}."
            )

        # The historical helper accepts a filename string and
        # performs Path(filename).stem internally.
        try:
            filename_id = int(recording_id_from_name(name))
        except ValueError as exc:
            raise SystemExit(
                f"STOP: invalid source filename for REC {rid}: {name}"
            ) from exc

        if filename_id != rid:
            raise SystemExit(
                f"STOP: recording-ID/filename mismatch for REC {rid}."
            )

        # Lighting selection comes from the reviewed manifest.
        # No filename-based reclassification is performed here.
        if domain == "DAY":
            path = DATA_DIR / name

            if not path.is_file():
                raise SystemExit(
                    f"STOP: DAY source MCAP not found: {path}"
                )

            day_paths.append(path)

    if (
        domain_counts["DAY"] != EXPECTED_DAY_COUNT
        or domain_counts["NIGHT"] != EXPECTED_NIGHT_COUNT
        or len(day_paths) != EXPECTED_DAY_COUNT
    ):
        raise SystemExit(
            "STOP: expected exactly 25 DAY and 7 NIGHT recordings."
        )

    # Preserve the historical exporter's path-based batch ordering.
    # Camera-message lists are not sorted or otherwise changed.
    return sorted(day_paths)


def main():
    if OUTPUT_ROOT.exists():
        raise SystemExit(
            f"STOP: batch output already exists: {OUTPUT_ROOT}"
        )

    # Validate the complete manifest and all selected DAY paths
    # before creating any output directories or files.
    mcaps = load_batch_mcaps()

    # Exclusive directory creation also protects against the output
    # appearing between the initial check and this operation.
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=False)

    print(f"Batch ID: {BATCH_ID}")
    print("Protocol reference: dataset_protocol_v3")
    print(f"Batch manifest: {BATCH_MANIFEST}")
    print(f"Output root: {OUTPUT_ROOT}")
    print(f"Found {len(mcaps)} MCAP files to process.")

    all_rows = []

    for i, path in enumerate(mcaps, start=1):
        print(f"\n[{i}/{len(mcaps)}]")
        rows = process_recording(path)
        all_rows.extend(rows)

    master_metadata = OUTPUT_ROOT / "master_metadata.csv"

    if all_rows:
        with open(master_metadata, "w", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=list(all_rows[0].keys())
            )
            writer.writeheader()
            writer.writerows(all_rows)

    print("\n" + "=" * 70)
    print("BATCH EXTRACTION COMPLETE")
    print("=" * 70)
    print(f"Total synchronized samples: {len(all_rows)}")
    print(f"Master metadata: {master_metadata}")


if __name__ == "__main__":
    main()