from pathlib import Path
import csv
import math
from statistics import mean, median

from mcap.reader import make_reader
from mcap_ros2.decoder import DecoderFactory


DATA_DIR = Path("/workspace/data")
OUTPUT_CSV = Path("/workspace/extracted/sync_analysis_all_mcaps.csv")

FILL_TOPIC = "/processing/crusher/fill_level"
NARROW_TOPIC = "/sensor/camera/front_narrow/image_raw/compressed/throttled"
WIDE_TOPIC = "/sensor/camera/front_wide/image_raw/compressed/throttled"

MAX_DELTA_SECONDS = 1.0


def stamp_to_ns(stamp):
    return stamp.sec * 1_000_000_000 + stamp.nanosec


def nearest_timestamp(target_ns, timestamps):
    """
    Returns:
        nearest_index
        signed_delta_seconds
        abs_delta_seconds
    """

    if not timestamps:
        return None, None, None

    # Simple search is fine here because dataset size is small.
    nearest_index = min(
        range(len(timestamps)),
        key=lambda i: abs(timestamps[i] - target_ns)
    )

    nearest_ns = timestamps[nearest_index]

    signed_delta = (nearest_ns - target_ns) / 1e9
    abs_delta = abs(signed_delta)

    return nearest_index, signed_delta, abs_delta


def percentile(values, p):
    if not values:
        return None

    values = sorted(values)

    if len(values) == 1:
        return values[0]

    k = (len(values) - 1) * p
    f = math.floor(k)
    c = math.ceil(k)

    if f == c:
        return values[int(k)]

    return values[f] * (c - k) + values[c] * (k - f)


def analyze_file(path):
    fill_messages = []
    narrow_timestamps = []
    wide_timestamps = []

    with open(path, "rb") as f:
        reader = make_reader(
            f,
            decoder_factories=[DecoderFactory()]
        )

        for schema, channel, message, ros_msg in reader.iter_decoded_messages():
            topic = channel.topic

            if topic == FILL_TOPIC:
                fill_messages.append(
                    {
                        "timestamp_ns": stamp_to_ns(ros_msg.header.stamp),
                        "value": float(ros_msg.data),
                    }
                )

            elif topic == NARROW_TOPIC:
                narrow_timestamps.append(
                    stamp_to_ns(ros_msg.header.stamp)
                )

            elif topic == WIDE_TOPIC:
                wide_timestamps.append(
                    stamp_to_ns(ros_msg.header.stamp)
                )

    result = {
        "file": path.name,
        "fill_count": len(fill_messages),
        "narrow_count": len(narrow_timestamps),
        "wide_count": len(wide_timestamps),
    }

    # Skip unusable MCAPs
    if not fill_messages or not narrow_timestamps or not wide_timestamps:
        result["usable"] = False
        return result

    narrow_deltas = []
    wide_deltas = []

    both_valid = 0
    narrow_failed = 0
    wide_failed = 0
    both_failed = 0

    worst_narrow = 0.0
    worst_wide = 0.0

    for fill in fill_messages:
        fill_ts = fill["timestamp_ns"]

        _, _, narrow_abs = nearest_timestamp(
            fill_ts,
            narrow_timestamps
        )

        _, _, wide_abs = nearest_timestamp(
            fill_ts,
            wide_timestamps
        )

        narrow_deltas.append(narrow_abs)
        wide_deltas.append(wide_abs)

        worst_narrow = max(worst_narrow, narrow_abs)
        worst_wide = max(worst_wide, wide_abs)

        narrow_ok = narrow_abs <= MAX_DELTA_SECONDS
        wide_ok = wide_abs <= MAX_DELTA_SECONDS

        if narrow_ok and wide_ok:
            both_valid += 1

        elif not narrow_ok and not wide_ok:
            both_failed += 1

        elif not narrow_ok:
            narrow_failed += 1

        elif not wide_ok:
            wide_failed += 1

    result.update(
        {
            "usable": True,
            "both_valid": both_valid,
            "rejected": len(fill_messages) - both_valid,

            "narrow_failed_only": narrow_failed,
            "wide_failed_only": wide_failed,
            "both_failed": both_failed,

            "narrow_mean": mean(narrow_deltas),
            "narrow_median": median(narrow_deltas),
            "narrow_p95": percentile(narrow_deltas, 0.95),
            "narrow_max": max(narrow_deltas),

            "wide_mean": mean(wide_deltas),
            "wide_median": median(wide_deltas),
            "wide_p95": percentile(wide_deltas, 0.95),
            "wide_max": max(wide_deltas),

            "valid_percent": (
                both_valid / len(fill_messages) * 100
            ),
        }
    )

    return result


def fmt(value):
    if value is None:
        return "-"
    return f"{value:.3f}"


def main():
    mcaps = sorted(DATA_DIR.glob("*.mcap"))

    if not mcaps:
        print("No MCAP files found.")
        return

    print(f"\nFound {len(mcaps)} MCAP files\n")

    results = []

    for i, path in enumerate(mcaps, start=1):
        print(f"[{i}/{len(mcaps)}] Analyzing sync: {path.name}")

        try:
            result = analyze_file(path)
            results.append(result)

        except Exception as e:
            print(f"ERROR: {path.name}: {e}")

    print("\n")
    print("=" * 155)
    print(
        "SYNCHRONIZATION ANALYSIS "
        f"(maximum allowed |Δt| = {MAX_DELTA_SECONDS:.1f} s)"
    )
    print("=" * 155)

    print(
        f"{'File':40}"
        f"{'Fill':>7}"
        f"{'Valid':>8}"
        f"{'Reject':>8}"
        f"{'Valid%':>9}"
        f"{'N mean':>10}"
        f"{'N med':>10}"
        f"{'N P95':>10}"
        f"{'N max':>10}"
        f"{'W mean':>10}"
        f"{'W med':>10}"
        f"{'W P95':>10}"
        f"{'W max':>10}"
    )

    print("-" * 155)

    total_fill = 0
    total_valid = 0
    total_rejected = 0

    usable_results = []

    for r in results:

        if not r["usable"]:
            print(
                f"{r['file'][:40]:40}"
                f"{r['fill_count']:7d}"
                f"{'SKIP':>8}"
                f"{'':>8}"
                f"{'':>9}"
                f"   Missing required camera/fill topics"
            )
            continue

        usable_results.append(r)

        total_fill += r["fill_count"]
        total_valid += r["both_valid"]
        total_rejected += r["rejected"]

        print(
            f"{r['file'][:40]:40}"
            f"{r['fill_count']:7d}"
            f"{r['both_valid']:8d}"
            f"{r['rejected']:8d}"
            f"{r['valid_percent']:8.1f}%"
            f"{fmt(r['narrow_mean']):>10}"
            f"{fmt(r['narrow_median']):>10}"
            f"{fmt(r['narrow_p95']):>10}"
            f"{fmt(r['narrow_max']):>10}"
            f"{fmt(r['wide_mean']):>10}"
            f"{fmt(r['wide_median']):>10}"
            f"{fmt(r['wide_p95']):>10}"
            f"{fmt(r['wide_max']):>10}"
        )

    print("-" * 155)

    valid_percentage = (
        total_valid / total_fill * 100
        if total_fill else 0
    )

    print(
        f"{'TOTAL':40}"
        f"{total_fill:7d}"
        f"{total_valid:8d}"
        f"{total_rejected:8d}"
        f"{valid_percentage:8.1f}%"
    )

    # Save detailed per-recording summary
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "file",
        "fill_count",
        "narrow_count",
        "wide_count",
        "both_valid",
        "rejected",
        "valid_percent",
        "narrow_failed_only",
        "wide_failed_only",
        "both_failed",
        "narrow_mean",
        "narrow_median",
        "narrow_p95",
        "narrow_max",
        "wide_mean",
        "wide_median",
        "wide_p95",
        "wide_max",
    ]

    with open(OUTPUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames
        )

        writer.writeheader()

        for r in usable_results:
            writer.writerow(
                {field: r.get(field) for field in fieldnames}
            )

    print(f"\nSummary CSV saved to:")
    print(OUTPUT_CSV)

    print("\nFailure breakdown:")

    for r in usable_results:
        if r["rejected"] > 0:
            print(
                f"{r['file']}: "
                f"narrow-only fail={r['narrow_failed_only']}, "
                f"wide-only fail={r['wide_failed_only']}, "
                f"both fail={r['both_failed']}"
            )


if __name__ == "__main__":
    main()