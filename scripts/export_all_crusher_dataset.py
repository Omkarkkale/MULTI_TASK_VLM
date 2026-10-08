from pathlib import Path
import csv

from mcap.reader import make_reader
from mcap_ros2.decoder import DecoderFactory


DATA_DIR = Path("/workspace/data")
OUTPUT_ROOT = Path("/workspace/extracted/crusher_dataset_v2")

FILL_TOPIC = "/processing/crusher/fill_level"
NARROW_TOPIC = "/sensor/camera/front_narrow/image_raw/compressed/throttled"
WIDE_TOPIC = "/sensor/camera/front_wide/image_raw/compressed/throttled"

MAX_DELTA_SECONDS = 1.0

# Old tiny recording excluded
EXCLUDED_FILES = {
    "2026_08_22-13_10_54_eye_0.mcap"
}


def stamp_to_ns(stamp):
    return stamp.sec * 1_000_000_000 + stamp.nanosec


def nearest_index(target_ns, timestamps):
    return min(
        range(len(timestamps)),
        key=lambda i: abs(timestamps[i] - target_ns)
    )


def recording_id_from_name(filename):
    stem = Path(filename).stem
    return stem.split("_")[-1]


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


def main():
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    mcaps = sorted(
        p for p in DATA_DIR.glob("*.mcap")
        if p.name not in EXCLUDED_FILES
    )

    if not mcaps:
        print("No usable MCAP files found.")
        return

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