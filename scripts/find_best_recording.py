from pathlib import Path
from itertools import combinations
from collections import Counter
import csv
import statistics


DATASET_ROOT = Path("/workspace/extracted/crusher_dataset_v2")
METADATA = DATASET_ROOT / "master_metadata_clean.csv"

# Desired approximate proportions
TARGET_TRAIN = 0.70
TARGET_VAL = 0.15
TARGET_TEST = 0.15

BINS = [
    (0, 20),
    (20, 40),
    (40, 60),
    (60, 80),
    (80, 101),
]

BIN_NAMES = [
    "0-19",
    "20-39",
    "40-59",
    "60-79",
    "80-100",
]


def get_distribution(rows):
    values = [float(r["fill_level"]) for r in rows]

    counts = []

    for low, high in BINS:
        count = sum(low <= v < high for v in values)
        counts.append(count)

    proportions = [
        c / len(values)
        for c in counts
    ]

    return {
        "n": len(values),
        "min": min(values),
        "max": max(values),
        "mean": statistics.mean(values),
        "median": statistics.median(values),
        "std": statistics.pstdev(values),
        "counts": counts,
        "props": proportions,
    }


def distribution_distance(a, reference):
    """
    Mean absolute difference between fill-bin proportions.
    Smaller = closer to overall dataset distribution.
    """
    return sum(
        abs(x - y)
        for x, y in zip(a["props"], reference["props"])
    ) / len(BINS)


def score_split(train, val, test, overall, total):

    train_ratio = train["n"] / total
    val_ratio = val["n"] / total
    test_ratio = test["n"] / total

    # --------------------------------------------------
    # 1. Split-size penalty
    # --------------------------------------------------

    size_penalty = (
        abs(train_ratio - TARGET_TRAIN)
        + abs(val_ratio - TARGET_VAL)
        + abs(test_ratio - TARGET_TEST)
    )

    # --------------------------------------------------
    # 2. Distribution penalty
    # --------------------------------------------------

    distribution_penalty = (
        distribution_distance(train, overall)
        + distribution_distance(val, overall)
        + distribution_distance(test, overall)
    )

    # --------------------------------------------------
    # 3. Missing-bin penalty
    #
    # Strongly penalize validation/test if an entire
    # fill-level region is absent.
    # --------------------------------------------------

    missing_bin_penalty = 0

    for split in [val, test]:
        missing_bins = sum(
            count == 0
            for count in split["counts"]
        )

        missing_bin_penalty += missing_bins * 0.50

    # --------------------------------------------------
    # 4. Extreme coverage penalty
    #
    # We especially care about low and high fill levels.
    # --------------------------------------------------

    extreme_penalty = 0

    for split in [val, test]:

        low_prop = split["props"][0]
        high_prop = split["props"][-1]

        # Penalize extremely weak representation
        if low_prop < 0.03:
            extreme_penalty += (0.03 - low_prop) * 5

        if high_prop < 0.03:
            extreme_penalty += (0.03 - high_prop) * 5

    # --------------------------------------------------
    # 5. Mean shift penalty
    # --------------------------------------------------

    mean_penalty = (
        abs(train["mean"] - overall["mean"])
        + abs(val["mean"] - overall["mean"])
        + abs(test["mean"] - overall["mean"])
    ) / 100.0

    # Weighted final score
    score = (
        3.0 * size_penalty
        + 4.0 * distribution_penalty
        + missing_bin_penalty
        + extreme_penalty
        + mean_penalty
    )

    return score


def print_split(name, recs, stats, total):

    print(
        f"{name:<5} "
        f"recs={','.join(sorted(recs, key=int)):<20} "
        f"N={stats['n']:<4} "
        f"({100 * stats['n'] / total:5.1f}%) "
        f"range={stats['min']:.0f}-{stats['max']:.0f}% "
        f"mean={stats['mean']:.1f}%"
    )

    coverage = " | ".join(
        f"{name_}:{count}"
        for name_, count in zip(
            BIN_NAMES,
            stats["counts"]
        )
    )

    print(f"      {coverage}")


def main():

    with open(METADATA, newline="") as f:
        rows = list(csv.DictReader(f))

    recordings = sorted(
        set(r["recording_id"] for r in rows),
        key=int
    )

    total = len(rows)
    overall = get_distribution(rows)

    rows_by_recording = {}

    for rec in recordings:
        rows_by_recording[rec] = [
            r for r in rows
            if r["recording_id"] == rec
        ]

    candidates = []

    # --------------------------------------------------
    # Search all assignments.
    #
    # With 8 recordings this is tiny, so brute force is
    # perfectly fine.
    # --------------------------------------------------

    recording_set = set(recordings)

    # Validation: 1 or 2 recordings
    for val_size in [1, 2]:

        for val_tuple in combinations(
            recordings,
            val_size
        ):

            val_recs = set(val_tuple)

            remaining_after_val = (
                recording_set - val_recs
            )

            # Test: 1 or 2 recordings
            for test_size in [1, 2]:

                for test_tuple in combinations(
                    sorted(
                        remaining_after_val,
                        key=int
                    ),
                    test_size
                ):

                    test_recs = set(test_tuple)

                    train_recs = (
                        recording_set
                        - val_recs
                        - test_recs
                    )

                    if not train_recs:
                        continue

                    train_rows = [
                        r
                        for rec in train_recs
                        for r in rows_by_recording[rec]
                    ]

                    val_rows = [
                        r
                        for rec in val_recs
                        for r in rows_by_recording[rec]
                    ]

                    test_rows = [
                        r
                        for rec in test_recs
                        for r in rows_by_recording[rec]
                    ]

                    train_stats = get_distribution(
                        train_rows
                    )

                    val_stats = get_distribution(
                        val_rows
                    )

                    test_stats = get_distribution(
                        test_rows
                    )

                    # --------------------------------------------------
                    # Basic constraints
                    # --------------------------------------------------

                    train_ratio = (
                        train_stats["n"] / total
                    )

                    val_ratio = (
                        val_stats["n"] / total
                    )

                    test_ratio = (
                        test_stats["n"] / total
                    )

                    # Keep only reasonably sized splits
                    if not (0.60 <= train_ratio <= 0.80):
                        continue

                    if not (0.07 <= val_ratio <= 0.25):
                        continue

                    if not (0.10 <= test_ratio <= 0.25):
                        continue

                    score = score_split(
                        train_stats,
                        val_stats,
                        test_stats,
                        overall,
                        total,
                    )

                    candidates.append(
                        {
                            "score": score,
                            "train_recs": train_recs,
                            "val_recs": val_recs,
                            "test_recs": test_recs,
                            "train": train_stats,
                            "val": val_stats,
                            "test": test_stats,
                        }
                    )

    candidates.sort(
        key=lambda x: x["score"]
    )

    print("=" * 110)
    print("RECORDING-LEVEL SPLIT SEARCH")
    print("=" * 110)

    print(f"\nTotal clean samples: {total}")
    print(
        f"Recordings: "
        f"{', '.join(recordings)}"
    )

    print("\nOverall distribution:")

    for name, count, prop in zip(
        BIN_NAMES,
        overall["counts"],
        overall["props"],
    ):
        print(
            f"  {name:>6}% : "
            f"{count:>4} "
            f"({100 * prop:5.1f}%)"
        )

    print(
        f"\nValid candidate splits found: "
        f"{len(candidates)}"
    )

    print("\n" + "=" * 110)
    print("TOP 10 CANDIDATE SPLITS")
    print("=" * 110)

    for rank, candidate in enumerate(
        candidates[:10],
        start=1
    ):

        print(
            f"\n#{rank} "
            f"Score = {candidate['score']:.4f}"
        )

        print_split(
            "TRAIN",
            candidate["train_recs"],
            candidate["train"],
            total,
        )

        print_split(
            "VAL",
            candidate["val_recs"],
            candidate["val"],
            total,
        )

        print_split(
            "TEST",
            candidate["test_recs"],
            candidate["test"],
            total,
        )

    print("\n" + "=" * 110)

    if candidates:

        best = candidates[0]

        print("BEST DATASET-BASED CANDIDATE")
        print("=" * 110)

        print_split(
            "TRAIN",
            best["train_recs"],
            best["train"],
            total,
        )

        print_split(
            "VAL",
            best["val_recs"],
            best["val"],
            total,
        )

        print_split(
            "TEST",
            best["test_recs"],
            best["test"],
            total,
        )

        print(
            "\nIMPORTANT: This is a statistical "
            "recommendation only."
        )

        print(
            "Do not create the final split yet. "
            "Review this candidate first."
        )

    else:
        print(
            "No candidate split satisfied "
            "the constraints."
        )


if __name__ == "__main__":
    main()