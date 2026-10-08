import csv
import math
from pathlib import Path
from collections import Counter

RESULTS = Path("/workspace/results/openrouter/full_benchmark")
REPORTS = Path("/workspace/results/openrouter/reports")

MODELS = {
    "qwen35_9b": {
        "name": "Qwen3.5-9B",
        "normal": "qwen35_9b_test337.csv",
        "night": "qwen35_9b_night859.csv",
    },
    "deepseek_v41_flash": {
        "name": "DeepSeek V4.1 Flash",
        "normal": "deepseek_v41_flash_test337.csv",
        "night": "deepseek_v41_flash_night859.csv",
    },
    "qwen38_27b": {
        "name": "Qwen3.8-27B",
        "normal": "qwen38_27b_test337.csv",
        "night": "qwen38_27b_night859.csv",
    },
    "glm_5v_turbo": {
        "name": "GLM-5V-Turbo",
        "normal": "glm_5v_turbo_test337.csv",
        "night": "glm_5v_turbo_night859.csv",
    },
}

BINS = [
    ("0-19", 0, 19),
    ("20-39", 20, 39),
    ("40-59", 40, 59),
    ("60-79", 60, 79),
    ("80-100", 80, 100),
]


def load_csv(path):
    rows = []

    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            rows.append(row)

    return rows


def final_successes(rows):
    """
    Keep the latest successful prediction for each eval_index.
    Historical invalid/API attempts remain excluded from accuracy.
    """
    successful = {}

    for row in rows:
        if row.get("status") == "success":
            successful[row["eval_index"]] = row

    return list(successful.values())


def attempt_counts(rows):
    invalid = sum(
        1 for r in rows
        if r.get("status") == "invalid_output"
    )

    api_errors = sum(
        1 for r in rows
        if r.get("status") == "api_error"
    )

    return invalid, api_errors


def calculate_metrics(rows, expected_total):
    success_rows = final_successes(rows)

    gt = [float(r["ground_truth"]) for r in success_rows]
    pred = [float(r["prediction"]) for r in success_rows]

    errors = [abs(a - b) for a, b in zip(gt, pred)]

    n = len(errors)

    mae = sum(errors) / n

    sorted_errors = sorted(errors)

    if n % 2:
        median = sorted_errors[n // 2]
    else:
        median = (
            sorted_errors[n // 2 - 1] +
            sorted_errors[n // 2]
        ) / 2

    rmse = math.sqrt(
        sum(e * e for e in errors) / n
    )

    invalid, api_errors = attempt_counts(rows)

    bin_metrics = {}

    for label, low, high in BINS:
        selected = [
            abs(float(r["ground_truth"]) - float(r["prediction"]))
            for r in success_rows
            if low <= float(r["ground_truth"]) <= high
        ]

        bin_metrics[label] = {
            "n": len(selected),
            "mae": (
                sum(selected) / len(selected)
                if selected else None
            ),
        }

    preds = [float(r["prediction"]) for r in success_rows]
    gts = [float(r["ground_truth"]) for r in success_rows]

    counter = Counter(preds)
    common = counter.most_common()

    top3_count = sum(c for _, c in common[:3])

    return {
        "success": n,
        "expected_total": expected_total,
        "coverage": 100 * n / expected_total,
        "invalid_attempts": invalid,
        "api_errors": api_errors,
        "mae": mae,
        "median": median,
        "rmse": rmse,
        "bins": bin_metrics,
        "unique_gt": len(set(gts)),
        "unique_pred": len(set(preds)),
        "common": common,
        "top3_count": top3_count,
        "top3_pct": 100 * top3_count / n,
    }


def fmt(value):
    if value is None:
        return "N/A"
    return f"{value:.2f}"


def main():
    REPORTS.mkdir(parents=True, exist_ok=True)

    all_results = {}

    for alias, info in MODELS.items():

        normal_rows = load_csv(
            RESULTS / info["normal"]
        )

        night_rows = load_csv(
            RESULTS / info["night"]
        )

        normal = calculate_metrics(
            normal_rows,
            expected_total=337
        )

        night = calculate_metrics(
            night_rows,
            expected_total=859
        )

        all_results[alias] = {
            "name": info["name"],
            "normal": normal,
            "night": night,
        }

    report = []

    report.append("=" * 88)
    report.append("NORMAL VS NIGHT ZERO-SHOT VLM COMPARISON")
    report.append("=" * 88)

    report.append("")
    report.append("EXPERIMENTAL CONTEXT")
    report.append("-" * 88)

    report.append(
        "Normal benchmark: 337 frozen samples from recording chunks 39 and 118."
    )
    report.append(
        "Night benchmark : 859 synchronized and visually accepted samples."
    )
    report.append(
        "Both benchmarks use the same crusher fill-level task, two camera views, "
        "and fixed zero-shot prompt."
    )

    report.append("")
    report.append(
        "IMPORTANT: The normal and night datasets have different ground-truth "
        "fill-level distributions. Therefore, overall normal-vs-night MAE "
        "differences cannot by themselves be interpreted as a pure lighting effect."
    )

    # ---------------------------------------------------------
    # Overall
    # ---------------------------------------------------------

    report.append("")
    report.append("=" * 88)
    report.append("1. OVERALL ACCURACY AND OUTPUT RELIABILITY")
    report.append("=" * 88)

    header = (
        f"{'Model':<24}"
        f"{'Condition':<10}"
        f"{'Valid':>10}"
        f"{'Coverage':>11}"
        f"{'MAE':>10}"
        f"{'Median':>10}"
        f"{'RMSE':>10}"
    )

    report.append(header)
    report.append("-" * len(header))

    for result in all_results.values():

        for condition in ["normal", "night"]:
            m = result[condition]

            report.append(
                f"{result['name']:<24}"
                f"{condition.capitalize():<10}"
                f"{m['success']:>4}/{m['expected_total']:<5}"
                f"{m['coverage']:>10.2f}%"
                f"{m['mae']:>10.2f}"
                f"{m['median']:>10.2f}"
                f"{m['rmse']:>10.2f}"
            )

    # ---------------------------------------------------------
    # Shared-bin comparison
    # ---------------------------------------------------------

    report.append("")
    report.append("=" * 88)
    report.append("2. FILL-RANGE MAE: NORMAL VS NIGHT")
    report.append("=" * 88)

    report.append(
        "Comparing errors within the same ground-truth fill ranges reduces the "
        "influence of the different overall target distributions."
    )

    for result in all_results.values():

        report.append("")
        report.append(result["name"])
        report.append("-" * len(result["name"]))

        report.append(
            f"{'GT range':<12}"
            f"{'Normal MAE':>14}"
            f"{'Normal n':>11}"
            f"{'Night MAE':>14}"
            f"{'Night n':>11}"
            f"{'Δ Night-Normal':>18}"
        )

        for label, _, _ in BINS:

            nrm = result["normal"]["bins"][label]
            ngt = result["night"]["bins"][label]

            if nrm["mae"] is not None and ngt["mae"] is not None:
                delta = ngt["mae"] - nrm["mae"]
                delta_text = f"{delta:+.2f}"
            else:
                delta_text = "N/A"

            report.append(
                f"{label + '%':<12}"
                f"{fmt(nrm['mae']):>14}"
                f"{nrm['n']:>11}"
                f"{fmt(ngt['mae']):>14}"
                f"{ngt['n']:>11}"
                f"{delta_text:>18}"
            )

    # ---------------------------------------------------------
    # Prediction granularity
    # ---------------------------------------------------------

    report.append("")
    report.append("=" * 88)
    report.append("3. PREDICTION GRANULARITY")
    report.append("=" * 88)

    for result in all_results.values():

        report.append("")
        report.append(result["name"])
        report.append("-" * len(result["name"]))

        for condition in ["normal", "night"]:

            m = result[condition]

            top3 = ", ".join(
                f"{value:.0f}% ({100*count/m['success']:.1f}%)"
                for value, count in m["common"][:3]
            )

            report.append(
                f"{condition.capitalize():<8}: "
                f"GT unique={m['unique_gt']}, "
                f"prediction unique={m['unique_pred']}, "
                f"top-3 concentration={m['top3_pct']:.1f}%"
            )

            report.append(
                f"          Most common: {top3}"
            )

    # ---------------------------------------------------------
    # Reliability
    # ---------------------------------------------------------

    report.append("")
    report.append("=" * 88)
    report.append("4. OUTPUT FORMAT RELIABILITY")
    report.append("=" * 88)

    for result in all_results.values():

        n = result["normal"]
        d = result["night"]

        report.append("")
        report.append(result["name"])

        report.append(
            f"  Normal: valid={n['success']}/{n['expected_total']} "
            f"({n['coverage']:.2f}%), "
            f"invalid attempts={n['invalid_attempts']}, "
            f"API errors={n['api_errors']}"
        )

        report.append(
            f"  Night : valid={d['success']}/{d['expected_total']} "
            f"({d['coverage']:.2f}%), "
            f"invalid attempts={d['invalid_attempts']}, "
            f"API errors={d['api_errors']}"
        )

    # ---------------------------------------------------------
    # Interpretation
    # ---------------------------------------------------------

    report.append("")
    report.append("=" * 88)
    report.append("5. DEFENSIBLE INTERPRETATION")
    report.append("=" * 88)

    report.append("")
    report.append(
        "The overall MAE values are descriptive results for each benchmark, "
        "but the difference between normal and night overall MAE should not "
        "be interpreted directly as the effect of lighting. The two datasets "
        "contain different proportions of low, medium, and high crusher fill levels."
    )

    report.append("")
    report.append(
        "The fill-range comparison is more informative because it compares "
        "model errors within approximately equivalent ground-truth ranges. "
        "However, this is still an observational comparison rather than a "
        "perfectly controlled paired lighting experiment: the normal and night "
        "images are not necessarily the same physical crusher states captured "
        "under two lighting conditions."
    )

    report.append("")
    report.append(
        "Across the evaluated zero-shot models, prediction distributions should "
        "also be considered alongside MAE. Strong concentration on a small set "
        "of preferred percentages can make a model appear accurate in ranges "
        "that happen to align with those preferred outputs while producing "
        "large systematic errors elsewhere."
    )

    report.append("")
    report.append(
        "These results therefore motivate domain-specific adaptation and "
        "fine-tuning for continuous crusher fill-level estimation rather than "
        "relying only on generic zero-shot numerical estimates."
    )

    # ---------------------------------------------------------
    # Per-model interpretations
    # ---------------------------------------------------------

    report.append("")
    report.append("=" * 88)
    report.append("6. PER-MODEL INTERPRETATION")
    report.append("=" * 88)

    for result in all_results.values():

        name = result["name"]
        n = result["normal"]
        d = result["night"]

        report.append("")
        report.append(name)
        report.append("-" * len(name))

        report.append(
            f"Overall MAE changed from {n['mae']:.2f} pp under the normal "
            f"benchmark to {d['mae']:.2f} pp under the night benchmark."
        )

        report.append(
            "This change should not by itself be attributed to lighting because "
            "the two benchmarks have different target distributions."
        )

        shared_deltas = []

        for label, _, _ in BINS:
            nb = n["bins"][label]
            db = d["bins"][label]

            if nb["mae"] is not None and db["mae"] is not None:
                shared_deltas.append(
                    (
                        label,
                        db["mae"] - nb["mae"],
                        nb["mae"],
                        db["mae"],
                        nb["n"],
                        db["n"],
                    )
                )

        if shared_deltas:
            report.append(
                "Within shared fill ranges:"
            )

            for label, delta, nmae, dmae, nn, dn in shared_deltas:
                direction = (
                    "higher"
                    if delta > 0
                    else "lower"
                    if delta < 0
                    else "unchanged"
                )

                report.append(
                    f"  {label}%: night MAE {dmae:.2f} pp vs "
                    f"normal {nmae:.2f} pp "
                    f"({abs(delta):.2f} pp {direction}; "
                    f"n={dn} night, n={nn} normal)."
                )

        report.append(
            f"Night predictions used {d['unique_pred']} distinct values "
            f"for {d['unique_gt']} distinct GT values, with the three most "
            f"frequent predictions accounting for {d['top3_pct']:.1f}% "
            f"of valid night outputs."
        )

        report.append(
            "This concentration should be considered when interpreting the "
            "range-specific errors."
        )

    report.append("")
    report.append("=" * 88)

    output = REPORTS / "normal_vs_night_four_model_comparison.txt"

    output.write_text(
        "\n".join(report)
    )

    print("\n".join(report))
    print()
    print(f"Report saved to: {output}")


if __name__ == "__main__":
    main()
