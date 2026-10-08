from pathlib import Path
import csv
import statistics
from collections import defaultdict


DATASET_ROOT = Path("/workspace/extracted/crusher_night_dataset_v1")
CLEAN_METADATA = DATASET_ROOT / "master_metadata.csv"


def percentile(values, p):
    values = sorted(values)

    if not values:
        return None

    index = (len(values) - 1) * p
    lower = int(index)
    upper = min(lower + 1, len(values) - 1)

    fraction = index - lower

    return (
        values[lower] * (1 - fraction)
        + values[upper] * fraction
    )


def stats(values):
    return {
        "count": len(values),
        "min": min(values),
        "max": max(values),
        "mean": statistics.mean(values),
        "median": statistics.median(values),
        "std": statistics.pstdev(values),
        "p05": percentile(values, 0.05),
        "p95": percentile(values, 0.95),
        "unique": len(set(values)),
    }


def main():

    if not CLEAN_METADATA.exists():
        print(f"ERROR: {CLEAN_METADATA} not found.")
        return

    with open(CLEAN_METADATA, newline="") as f:
        rows = list(csv.DictReader(f))

    recordings = defaultdict(list)
    all_values = []

    for row in rows:
        recording = row["recording_id"]
        value = float(row["fill_level"])

        recordings[recording].append(value)
        all_values.append(value)

    print()
    print("=" * 120)
    print("CLEAN DATASET DISTRIBUTION")
    print("=" * 120)

    print(
        f"{'Rec':>6}"
        f"{'Samples':>10}"
        f"{'Min':>8}"
        f"{'Max':>8}"
        f"{'Mean':>9}"
        f"{'Median':>10}"
        f"{'Std':>9}"
        f"{'P05':>8}"
        f"{'P95':>8}"
        f"{'Unique':>9}"
    )

    print("-" * 120)

    for recording in sorted(
        recordings,
        key=lambda x: int(x)
    ):
        s = stats(recordings[recording])

        print(
            f"{recording:>6}"
            f"{s['count']:>10}"
            f"{s['min']:>8.1f}"
            f"{s['max']:>8.1f}"
            f"{s['mean']:>9.1f}"
            f"{s['median']:>10.1f}"
            f"{s['std']:>9.1f}"
            f"{s['p05']:>8.1f}"
            f"{s['p95']:>8.1f}"
            f"{s['unique']:>9}"
        )

    print("-" * 120)

    overall = stats(all_values)

    print(
        f"{'ALL':>6}"
        f"{overall['count']:>10}"
        f"{overall['min']:>8.1f}"
        f"{overall['max']:>8.1f}"
        f"{overall['mean']:>9.1f}"
        f"{overall['median']:>10.1f}"
        f"{overall['std']:>9.1f}"
        f"{overall['p05']:>8.1f}"
        f"{overall['p95']:>8.1f}"
        f"{overall['unique']:>9}"
    )

    # Fill-level bins
    bins = [
        (0, 20),
        (20, 40),
        (40, 60),
        (60, 80),
        (80, 101),
    ]

    print("\n")
    print("=" * 90)
    print("FILL-LEVEL COVERAGE")
    print("=" * 90)

    print(
        f"{'Rec':>6}"
        f"{'0-19':>10}"
        f"{'20-39':>10}"
        f"{'40-59':>10}"
        f"{'60-79':>10}"
        f"{'80-100':>10}"
    )

    print("-" * 90)

    for recording in sorted(
        recordings,
        key=lambda x: int(x)
    ):

        values = recordings[recording]

        counts = []

        for low, high in bins:
            count = sum(
                low <= v < high
                for v in values
            )
            counts.append(count)

        print(
            f"{recording:>6}"
            + "".join(
                f"{count:>10}"
                for count in counts
            )
        )

    print("-" * 90)

    overall_counts = []

    for low, high in bins:
        count = sum(
            low <= v < high
            for v in all_values
        )
        overall_counts.append(count)

    print(
        f"{'ALL':>6}"
        + "".join(
            f"{count:>10}"
            for count in overall_counts
        )
    )

    print("\nTotal clean samples:", len(rows))


if __name__ == "__main__":
    main()