import csv
import os
import math
from collections import Counter, defaultdict

RESULT_DIR = "/workspace/results/openrouter/full_benchmark"
OUTPUT_DIR = "/workspace/results/openrouter/reports"
os.makedirs(OUTPUT_DIR, exist_ok=True)

MODELS = {
    "qwen35_9b": "Qwen3.5-9B",
    "deepseek_v41_flash": "DeepSeek V4.1 Flash",
    "qwen38_27b": "Qwen3.8-27B",
    "glm_5v_turbo": "GLM-5V-Turbo",
}

TEST_SIZE = 337

BINS = [
    (0, 19, "0-19%"),
    (20, 39, "20-39%"),
    (40, 59, "40-59%"),
    (60, 79, "60-79%"),
    (80, 100, "80-100%"),
]


def safe_float(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def load_model(alias):
    path = os.path.join(RESULT_DIR, f"{alias}_test337.csv")

    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))

    # Latest successful prediction for each eval_index.
    successes = {}
    for row in rows:
        if row.get("status") == "success":
            successes[row["eval_index"]] = row

    valid_rows = list(successes.values())

    invalid_count = sum(
        1 for r in rows if r.get("status") == "invalid_output"
    )
    api_error_count = sum(
        1 for r in rows if r.get("status") == "api_error"
    )

    errors = []
    preds = []
    gts = []

    for row in valid_rows:
        gt = safe_float(row.get("ground_truth"))
        pred = safe_float(row.get("prediction"))

        if gt is None or pred is None:
            continue

        gts.append(gt)
        preds.append(pred)
        errors.append(abs(gt - pred))

    mae = sum(errors) / len(errors)

    sorted_errors = sorted(errors)
    n = len(sorted_errors)

    if n % 2:
        median = sorted_errors[n // 2]
    else:
        median = (
            sorted_errors[n // 2 - 1] +
            sorted_errors[n // 2]
        ) / 2

    rmse = math.sqrt(
        sum(e * e for e in errors) / len(errors)
    )

    bin_errors = defaultdict(list)

    for gt, pred in zip(gts, preds):
        err = abs(gt - pred)

        for lo, hi, label in BINS:
            if lo <= gt <= hi:
                bin_errors[label].append(err)
                break

    bin_mae = {}

    for _, _, label in BINS:
        vals = bin_errors[label]

        if vals:
            bin_mae[label] = (
                sum(vals) / len(vals),
                len(vals),
            )
        else:
            bin_mae[label] = (None, 0)

    pred_counter = Counter(preds)

    unique_gt = len(set(gts))
    unique_pred = len(set(preds))

    dominant_pred, dominant_count = pred_counter.most_common(1)[0]
    dominant_pct = 100 * dominant_count / len(preds)

    div5 = sum(
        1 for p in preds
        if abs((p / 5) - round(p / 5)) < 1e-9
    )

    div10 = sum(
        1 for p in preds
        if abs((p / 10) - round(p / 10)) < 1e-9
    )

    total_cost = sum(
        safe_float(r.get("cost_usd")) or 0.0
        for r in rows
    )

    prompt_tokens = sum(
        int(float(r.get("prompt_tokens") or 0))
        for r in rows
    )

    completion_tokens = sum(
        int(float(r.get("completion_tokens") or 0))
        for r in rows
    )

    reasoning_tokens = sum(
        int(float(r.get("reasoning_tokens") or 0))
        for r in rows
    )

    total_tokens = sum(
        int(float(r.get("total_tokens") or 0))
        for r in rows
    )

    resolved_models = [
        r.get("resolved_model")
        for r in rows
        if r.get("resolved_model")
    ]

    resolved_model = (
        Counter(resolved_models).most_common(1)[0][0]
        if resolved_models
        else "unknown"
    )

    return {
        "alias": alias,
        "name": MODELS[alias],
        "resolved_model": resolved_model,
        "success": len(valid_rows),
        "invalid": invalid_count,
        "api_errors": api_error_count,
        "valid_rate": 100 * len(valid_rows) / TEST_SIZE,
        "mae": mae,
        "median": median,
        "rmse": rmse,
        "bin_mae": bin_mae,
        "unique_gt": unique_gt,
        "unique_pred": unique_pred,
        "dominant_pred": dominant_pred,
        "dominant_count": dominant_count,
        "dominant_pct": dominant_pct,
        "div5_pct": 100 * div5 / len(preds),
        "div10_pct": 100 * div10 / len(preds),
        "total_cost": total_cost,
        "cost_per_success": total_cost / len(valid_rows),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "reasoning_tokens": reasoning_tokens,
        "total_tokens": total_tokens,
        "pred_counter": pred_counter,
    }


results = [load_model(alias) for alias in MODELS]


lines = []

def add(s=""):
    lines.append(s)


add("=" * 100)
add("CRUSHER FILL-LEVEL ZERO-SHOT VLM COMPARISON")
add("=" * 100)
add()
add("Evaluation condition : Normal lighting")
add("Evaluation mode      : Zero-shot")
add("Frozen test samples  : 337")
add("Camera views/sample  : 2 (front_narrow + front_wide)")
add("Target               : Crusher fill level (0-100%)")
add()


add("1. OVERALL ACCURACY AND RELIABILITY")
add("-" * 100)
add(
    f"{'Model':<23}"
    f"{'Valid':>9}"
    f"{'Rate':>10}"
    f"{'MAE':>10}"
    f"{'Median':>10}"
    f"{'RMSE':>10}"
    f"{'Invalid':>10}"
    f"{'API Err':>10}"
)

for r in results:
    add(
        f"{r['name']:<23}"
        f"{r['success']:>5}/337"
        f"{r['valid_rate']:>9.2f}%"
        f"{r['mae']:>9.2f}"
        f"{r['median']:>10.2f}"
        f"{r['rmse']:>10.2f}"
        f"{r['invalid']:>10}"
        f"{r['api_errors']:>10}"
    )

add()


add("2. MAE BY GROUND-TRUTH FILL RANGE")
add("-" * 100)

header = f"{'Model':<23}"
for _, _, label in BINS:
    header += f"{label:>15}"
add(header)

for r in results:
    row = f"{r['name']:<23}"

    for _, _, label in BINS:
        value, n = r["bin_mae"][label]

        if value is None:
            cell = "N/A"
        else:
            cell = f"{value:.2f} (n={n})"

        row += f"{cell:>15}"

    add(row)

add()


add("3. PREDICTION GRANULARITY / CALIBRATION")
add("-" * 100)
add(
    f"{'Model':<23}"
    f"{'Unique GT':>12}"
    f"{'Unique Pred':>14}"
    f"{'Dominant':>12}"
    f"{'Frequency':>13}"
    f"{'% /5':>10}"
    f"{'% /10':>10}"
)

for r in results:
    add(
        f"{r['name']:<23}"
        f"{r['unique_gt']:>12}"
        f"{r['unique_pred']:>14}"
        f"{r['dominant_pred']:>11.1f}%"
        f"{r['dominant_pct']:>12.1f}%"
        f"{r['div5_pct']:>9.1f}%"
        f"{r['div10_pct']:>9.1f}%"
    )

add()


add("4. MOST COMMON PREDICTIONS")
add("-" * 100)

for r in results:
    add()
    add(r["name"])

    for pred, count in r["pred_counter"].most_common(10):
        pct = 100 * count / r["success"]
        add(f"  {pred:6.1f}% -> {count:3d} samples ({pct:5.1f}%)")

add()


add("5. API COST")
add("-" * 100)
add(
    f"{'Model':<23}"
    f"{'Total cost':>15}"
    f"{'Cost/valid':>15}"
    f"{'Total tokens':>18}"
)

for r in results:
    add(
        f"{r['name']:<23}"
        f"${r['total_cost']:>13.8f}"
        f"${r['cost_per_success']:>13.8f}"
        f"{r['total_tokens']:>18,}"
    )

add()


add("6. RESOLVED MODEL VERSIONS")
add("-" * 100)

for r in results:
    add(f"{r['name']:<23}: {r['resolved_model']}")

add()


add("7. OBSERVATIONS")
add("-" * 100)
add(
    "All four zero-shot VLMs produced substantially fewer unique prediction "
    "values than the number of distinct ground-truth fill levels."
)
add(
    "The models therefore exhibited coarse and concentrated numerical outputs "
    "rather than finely calibrated continuous fill-level estimates."
)
add(
    "Prediction concentration differed by model, so the behavior should not be "
    "interpreted as an identical failure mode across architectures."
)
add(
    "Errors should be interpreted together with fill-range performance and "
    "prediction concentration, because frequent middle-range predictions can "
    "produce relatively low MAE in middle fill ranges while causing large "
    "errors at high fill levels."
)
add(
    "DeepSeek accuracy metrics are computed only on valid numeric predictions; "
    "its lower valid-output rate must therefore be considered alongside MAE."
)
add(
    "Qwen3.5 was evaluated before the benchmark's final invalid-output handling "
    "policy was introduced, so its output-reliability accounting carries a "
    "methodological caveat."
)

add()
add("=" * 100)

output_path = os.path.join(
    OUTPUT_DIR,
    "normal_zero_shot_four_model_comparison.txt"
)

with open(output_path, "w") as f:
    f.write("\n".join(lines))

print("\n".join(lines))
print()
print(f"Report saved to: {output_path}")
