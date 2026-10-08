from pathlib import Path
from statistics import mean
from mcap.reader import make_reader
from mcap_ros2.decoder import DecoderFactory


DATA_DIR = Path("/workspace/data")

FILL_TOPIC = "/processing/crusher/fill_level"
NARROW_TOPIC = "/sensor/camera/front_narrow/image_raw/compressed/throttled"
WIDE_TOPIC = "/sensor/camera/front_wide/image_raw/compressed/throttled"


def ros_time_to_ns(stamp):
    return stamp.sec * 1_000_000_000 + stamp.nanosec


def analyze_mcap(path: Path):
    fill_values = []
    fill_timestamps = []

    counts = {
        FILL_TOPIC: 0,
        NARROW_TOPIC: 0,
        WIDE_TOPIC: 0,
    }

    first_log_time = None
    last_log_time = None

    with open(path, "rb") as f:
        reader = make_reader(
            f,
            decoder_factories=[DecoderFactory()]
        )

        for schema, channel, message, ros_msg in reader.iter_decoded_messages():

            if first_log_time is None:
                first_log_time = message.log_time

            last_log_time = message.log_time

            topic = channel.topic

            if topic in counts:
                counts[topic] += 1

            if topic == FILL_TOPIC:
                fill_values.append(float(ros_msg.data))

                if hasattr(ros_msg, "header"):
                    fill_timestamps.append(
                        ros_time_to_ns(ros_msg.header.stamp)
                    )

    result = {
        "file": path.name,
        "size_gb": path.stat().st_size / (1024 ** 3),
        "fill_count": counts[FILL_TOPIC],
        "narrow_count": counts[NARROW_TOPIC],
        "wide_count": counts[WIDE_TOPIC],
    }

    if first_log_time is not None and last_log_time is not None:
        result["duration_min"] = (
            last_log_time - first_log_time
        ) / 1e9 / 60
    else:
        result["duration_min"] = None

    if fill_values:
        sorted_values = sorted(fill_values)

        result["fill_min"] = min(fill_values)
        result["fill_max"] = max(fill_values)
        result["fill_mean"] = mean(fill_values)

        n = len(sorted_values)

        result["fill_p05"] = sorted_values[int(0.05 * (n - 1))]
        result["fill_p95"] = sorted_values[int(0.95 * (n - 1))]

        result["unique_fill_values"] = len(set(fill_values))
    else:
        result["fill_min"] = None
        result["fill_max"] = None
        result["fill_mean"] = None
        result["fill_p05"] = None
        result["fill_p95"] = None
        result["unique_fill_values"] = 0

    return result


def main():
    mcaps = sorted(DATA_DIR.glob("*.mcap"))

    if not mcaps:
        print("No MCAP files found in:", DATA_DIR)
        return

    print(f"\nFound {len(mcaps)} MCAP files\n")

    results = []

    for i, mcap_path in enumerate(mcaps, start=1):
        print(f"[{i}/{len(mcaps)}] Analyzing {mcap_path.name}...")
        try:
            result = analyze_mcap(mcap_path)
            results.append(result)
        except Exception as e:
            print(f"ERROR analyzing {mcap_path.name}: {e}")

    print("\n")
    print("=" * 140)
    print("MCAP SUMMARY")
    print("=" * 140)

    header = (
        f"{'File':40} "
        f"{'GB':>6} "
        f"{'Min':>8} "
        f"{'Fill':>8} "
        f"{'Nar':>8} "
        f"{'Wide':>8} "
        f"{'Min%':>7} "
        f"{'Max%':>7} "
        f"{'Mean%':>8} "
        f"{'P05':>7} "
        f"{'P95':>7} "
        f"{'Unique':>8}"
    )

    print(header)
    print("-" * 140)

    for r in results:
        print(
            f"{r['file'][:40]:40} "
            f"{r['size_gb']:6.2f} "
            f"{r['duration_min'] if r['duration_min'] is not None else 0:8.1f} "
            f"{r['fill_count']:8d} "
            f"{r['narrow_count']:8d} "
            f"{r['wide_count']:8d} "
            f"{r['fill_min'] if r['fill_min'] is not None else 0:7.1f} "
            f"{r['fill_max'] if r['fill_max'] is not None else 0:7.1f} "
            f"{r['fill_mean'] if r['fill_mean'] is not None else 0:8.1f} "
            f"{r['fill_p05'] if r['fill_p05'] is not None else 0:7.1f} "
            f"{r['fill_p95'] if r['fill_p95'] is not None else 0:7.1f} "
            f"{r['unique_fill_values']:8d}"
        )

    total_fill = sum(r["fill_count"] for r in results)
    total_narrow = sum(r["narrow_count"] for r in results)
    total_wide = sum(r["wide_count"] for r in results)

    print("-" * 140)
    print(
        f"{'TOTAL':40} "
        f"{'':6} "
        f"{'':8} "
        f"{total_fill:8d} "
        f"{total_narrow:8d} "
        f"{total_wide:8d}"
    )


if __name__ == "__main__":
    main()