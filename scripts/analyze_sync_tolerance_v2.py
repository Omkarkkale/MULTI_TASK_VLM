from pathlib import Path
import pandas as pd
import numpy as np

# ============================================================
# PATHS
# ============================================================

META = Path(
    "/workspace/extracted/crusher_dataset_v2/master_metadata.csv"
)

OUT_DIR = Path(
    "/workspace/results/synchronization_analysis"
)

DOC_DIR = Path(
    "/workspace/Documentation/01_Dataset"
)

OUT_DIR.mkdir(parents=True, exist_ok=True)
DOC_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# LOAD DATA
# ============================================================

df = pd.read_csv(META)

print("=" * 80)
print("SYNCHRONIZATION ANALYSIS - NORMAL DATASET V2")
print("=" * 80)

print(f"Rows in master metadata: {len(df)}")

# ============================================================
# REMOVE THE 15 KNOWN VISUAL-QC REJECTIONS
# ============================================================

reject_mask = (
    ((df["recording_id"] == 94) &
     (df["sample"].between(57, 61)))
    |
    ((df["recording_id"] == 118) &
     (df["sample"].between(104, 113)))
)

df_clean = df.loc[~reject_mask].copy()

print(f"Known QC-rejected rows: {reject_mask.sum()}")
print(f"Clean rows for main analysis: {len(df_clean)}")

# ============================================================
# CALCULATE DELTAS
# ============================================================

# Existing GT-camera absolute deltas
df_clean["gt_to_narrow_s"] = (
    df_clean["narrow_timestamp_ns"]
    - df_clean["fill_timestamp_ns"]
).abs() / 1e9

df_clean["gt_to_wide_s"] = (
    df_clean["wide_timestamp_ns"]
    - df_clean["fill_timestamp_ns"]
).abs() / 1e9

# NEW: direct camera-camera difference
df_clean["narrow_to_wide_s"] = (
    df_clean["narrow_timestamp_ns"]
    - df_clean["wide_timestamp_ns"]
).abs() / 1e9

# milliseconds for easier interpretation
df_clean["gt_to_narrow_ms"] = df_clean["gt_to_narrow_s"] * 1000
df_clean["gt_to_wide_ms"] = df_clean["gt_to_wide_s"] * 1000
df_clean["narrow_to_wide_ms"] = df_clean["narrow_to_wide_s"] * 1000

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def stats(series):
    return {
        "count": len(series),
        "mean_ms": series.mean(),
        "median_ms": series.median(),
        "p90_ms": series.quantile(0.90),
        "p95_ms": series.quantile(0.95),
        "p99_ms": series.quantile(0.99),
        "max_ms": series.max(),
    }


def print_stats(name, series):
    s = stats(series)

    print()
    print(name)
    print("-" * len(name))
    print(f"Samples : {s['count']}")
    print(f"Mean    : {s['mean_ms']:.3f} ms")
    print(f"Median  : {s['median_ms']:.3f} ms")
    print(f"P90     : {s['p90_ms']:.3f} ms")
    print(f"P95     : {s['p95_ms']:.3f} ms")
    print(f"P99     : {s['p99_ms']:.3f} ms")
    print(f"Maximum : {s['max_ms']:.3f} ms")

    return s


# ============================================================
# OVERALL STATISTICS
# ============================================================

narrow_stats = print_stats(
    "GT -> FRONT_NARROW",
    df_clean["gt_to_narrow_ms"]
)

wide_stats = print_stats(
    "GT -> FRONT_WIDE",
    df_clean["gt_to_wide_ms"]
)

camera_stats = print_stats(
    "FRONT_NARROW <-> FRONT_WIDE",
    df_clean["narrow_to_wide_ms"]
)

# ============================================================
# CUMULATIVE CAMERA-CAMERA TOLERANCE COUNTS
# ============================================================

thresholds_ms = [
    10,
    20,
    50,
    100,
    200,
    300,
    500,
    750,
    1000,
    1500,
    2000,
]

print()
print("CAMERA-TO-CAMERA CUMULATIVE TOLERANCE")
print("-------------------------------------")

threshold_rows = []

for threshold in thresholds_ms:
    count = (
        df_clean["narrow_to_wide_ms"] <= threshold
    ).sum()

    pct = count / len(df_clean) * 100

    threshold_rows.append({
        "threshold_ms": threshold,
        "samples": int(count),
        "percentage": pct,
    })

    print(
        f"<= {threshold:4d} ms : "
        f"{count:4d}/{len(df_clean)} "
        f"({pct:6.2f}%)"
    )

# ============================================================
# EXACT RANGE COUNTS
# ============================================================

bins = [
    0,
    10,
    20,
    50,
    100,
    200,
    300,
    500,
    750,
    1000,
    1500,
    2000,
    np.inf,
]

labels = [
    "0-10 ms",
    "10-20 ms",
    "20-50 ms",
    "50-100 ms",
    "100-200 ms",
    "200-300 ms",
    "300-500 ms",
    "500-750 ms",
    "750-1000 ms",
    "1000-1500 ms",
    "1500-2000 ms",
    ">2000 ms",
]

df_clean["camera_delta_range"] = pd.cut(
    df_clean["narrow_to_wide_ms"],
    bins=bins,
    labels=labels,
    right=True,
    include_lowest=True,
)

range_counts = (
    df_clean["camera_delta_range"]
    .value_counts(sort=False)
)

print()
print("CAMERA-TO-CAMERA DELTA RANGES")
print("-----------------------------")

for label in labels:
    count = int(range_counts.get(label, 0))
    pct = count / len(df_clean) * 100

    print(
        f"{label:>14} : "
        f"{count:4d} "
        f"({pct:6.2f}%)"
    )

# ============================================================
# PER-RECORDING STATISTICS
# ============================================================

recording_summary = (
    df_clean
    .groupby("recording_id")
    .agg(
        samples=("sample", "count"),

        narrow_mean_ms=("gt_to_narrow_ms", "mean"),
        narrow_median_ms=("gt_to_narrow_ms", "median"),
        narrow_p95_ms=(
            "gt_to_narrow_ms",
            lambda x: x.quantile(0.95)
        ),
        narrow_max_ms=("gt_to_narrow_ms", "max"),

        wide_mean_ms=("gt_to_wide_ms", "mean"),
        wide_median_ms=("gt_to_wide_ms", "median"),
        wide_p95_ms=(
            "gt_to_wide_ms",
            lambda x: x.quantile(0.95)
        ),
        wide_max_ms=("gt_to_wide_ms", "max"),

        camera_mean_ms=("narrow_to_wide_ms", "mean"),
        camera_median_ms=("narrow_to_wide_ms", "median"),
        camera_p95_ms=(
            "narrow_to_wide_ms",
            lambda x: x.quantile(0.95)
        ),
        camera_max_ms=("narrow_to_wide_ms", "max"),
    )
    .reset_index()
)

print()
print("PER-RECORDING CAMERA-TO-CAMERA SUMMARY")
print("--------------------------------------")

print(
    recording_summary[
        [
            "recording_id",
            "samples",
            "camera_mean_ms",
            "camera_median_ms",
            "camera_p95_ms",
            "camera_max_ms",
        ]
    ].to_string(
        index=False,
        float_format=lambda x: f"{x:.2f}"
    )
)

# ============================================================
# LARGEST CAMERA-CAMERA DELTAS
# ============================================================

largest = (
    df_clean.sort_values(
        "narrow_to_wide_ms",
        ascending=False
    )
    [
        [
            "recording_id",
            "sample",
            "fill_level",
            "front_narrow",
            "front_wide",
            "gt_to_narrow_ms",
            "gt_to_wide_ms",
            "narrow_to_wide_ms",
            "narrow_signed_delta_t_seconds",
            "wide_signed_delta_t_seconds",
        ]
    ]
    .head(30)
)

print()
print("TOP 30 LARGEST CAMERA-TO-CAMERA DIFFERENCES")
print("-------------------------------------------")
print(
    largest.to_string(
        index=False,
        float_format=lambda x: f"{x:.3f}"
    )
)

# ============================================================
# SAVE MACHINE-READABLE OUTPUTS
# ============================================================

df_clean.to_csv(
    OUT_DIR / "normal_v2_sync_per_sample.csv",
    index=False
)

recording_summary.to_csv(
    OUT_DIR / "normal_v2_sync_by_recording.csv",
    index=False
)

pd.DataFrame(threshold_rows).to_csv(
    OUT_DIR / "normal_v2_camera_tolerance_counts.csv",
    index=False
)

largest.to_csv(
    OUT_DIR / "normal_v2_largest_camera_deltas.csv",
    index=False
)

# ============================================================
# WRITE DOCUMENTATION
# ============================================================

doc = DOC_DIR / "synchronization_analysis.md"

with doc.open("w", encoding="utf-8") as f:

    f.write("# Camera Synchronization Analysis\n\n")

    f.write("Dataset: **Normal v2 clean dataset**\n\n")

    f.write(
        f"Master metadata synchronized rows: **{len(df)}**\n\n"
    )

    f.write(
        f"Visual-QC rejected rows: **{reject_mask.sum()}**\n\n"
    )

    f.write(
        f"Clean samples analyzed: **{len(df_clean)}**\n\n"
    )

    f.write("## Existing Synchronization Rule\n\n")

    f.write(
        "Each camera was independently matched to the "
        "nearest `/processing/crusher/fill_level` "
        "ROS `header.stamp`.\n\n"
    )

    f.write(
        "Maximum GT-to-camera tolerance: **1.0 second**.\n\n"
    )

    f.write(
        "No direct narrow-to-wide tolerance had previously "
        "been imposed.\n\n"
    )

    f.write("## GT to Front Narrow\n\n")

    for k, v in narrow_stats.items():
        if k == "count":
            f.write(f"- Count: {v}\n")
        else:
            f.write(
                f"- {k.replace('_ms','').replace('_',' ').title()}: "
                f"{v:.3f} ms\n"
            )

    f.write("\n## GT to Front Wide\n\n")

    for k, v in wide_stats.items():
        if k == "count":
            f.write(f"- Count: {v}\n")
        else:
            f.write(
                f"- {k.replace('_ms','').replace('_',' ').title()}: "
                f"{v:.3f} ms\n"
            )

    f.write("\n## Front Narrow to Front Wide\n\n")

    for k, v in camera_stats.items():
        if k == "count":
            f.write(f"- Count: {v}\n")
        else:
            f.write(
                f"- {k.replace('_ms','').replace('_',' ').title()}: "
                f"{v:.3f} ms\n"
            )

    f.write("\n## Cumulative Camera-to-Camera Tolerance\n\n")

    f.write("| Threshold | Samples | Percentage |\n")
    f.write("|---|---:|---:|\n")

    for row in threshold_rows:
        f.write(
            f"| <= {row['threshold_ms']} ms | "
            f"{row['samples']} | "
            f"{row['percentage']:.2f}% |\n"
        )

    f.write("\n## Interpretation\n\n")

    f.write(
        "The synchronization threshold should not be tightened "
        "solely from an arbitrary value. The empirical timing "
        "distribution should first be combined with visual review "
        "of samples containing large camera-to-camera offsets.\n\n"
    )

    f.write(
        "The final v3 synchronization rule should be selected "
        "after reviewing these statistics and inspecting the "
        "largest-delta image pairs.\n"
    )

print()
print("=" * 80)
print("OUTPUT FILES")
print("=" * 80)

print(
    OUT_DIR / "normal_v2_sync_per_sample.csv"
)

print(
    OUT_DIR / "normal_v2_sync_by_recording.csv"
)

print(
    OUT_DIR / "normal_v2_camera_tolerance_counts.csv"
)

print(
    OUT_DIR / "normal_v2_largest_camera_deltas.csv"
)

print(
    DOC_DIR / "synchronization_analysis.md"
)
