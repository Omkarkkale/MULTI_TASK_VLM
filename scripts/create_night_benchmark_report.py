from pathlib import Path
from collections import Counter
import argparse
import csv
import math
import statistics


RESULTS_DIR = Path("/workspace/results/openrouter/full_benchmark")
REPORT_DIR = Path("/workspace/results/openrouter/reports")

MODEL_FILES = {
    "qwen35_9b": "qwen35_9b_night859.csv",
    "deepseek_v41_flash": "deepseek_v41_flash_night859.csv",
    "qwen38_27b": "qwen38_27b_night859.csv",
    "glm_5v_turbo": "glm_5v_turbo_night859.csv",
}

TOTAL_TEST_SAMPLES = 859


def safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def main():
    parser = argparse.ArgumentParser(
        description="Create human-readable zero-shot benchmark report."
    )

    parser.add_argument(
        "--model",
        required=True,
        choices=MODEL_FILES.keys()
    )

    args = parser.parse_args()

    csv_path = RESULTS_DIR / MODEL_FILES[args.model]

    if not csv_path.exists():
        raise FileNotFoundError(csv_path)

    # ---------------------------------------------------------
    # Read all attempts
    # ---------------------------------------------------------

    with open(csv_path, newline="") as f:
        all_rows = list(csv.DictReader(f))

    latest_success = {}

    invalid_attempts = 0
    api_errors = 0

    total_cost = 0.0
    prompt_tokens = 0
    completion_tokens = 0
    reasoning_tokens = 0
    total_tokens = 0

    resolved_models = set()

    for row in all_rows:

        status = row.get("status", "").strip()

        if status == "invalid_output":
            invalid_attempts += 1

        elif status == "api_error":
            api_errors += 1

        # Cost/token totals include recorded attempts.
        total_cost += safe_float(row.get("cost_usd"))

        prompt_tokens += int(
            safe_float(row.get("prompt_tokens"))
        )

        completion_tokens += int(
            safe_float(row.get("completion_tokens"))
        )

        reasoning_tokens += int(
            safe_float(row.get("reasoning_tokens"))
        )

        total_tokens += int(
            safe_float(row.get("total_tokens"))
        )

        resolved = row.get("resolved_model", "").strip()

        if resolved:
            resolved_models.add(resolved)

        if status == "success":
            try:
                index = int(row["eval_index"])
                latest_success[index] = row
            except (ValueError, KeyError):
                pass

    rows = list(latest_success.values())

    if not rows:
        raise RuntimeError("No successful predictions found.")

    # ---------------------------------------------------------
    # Accuracy
    # ---------------------------------------------------------

    errors = [
        safe_float(row["absolute_error"])
        for row in rows
    ]

    mae = statistics.mean(errors)
    median_ae = statistics.median(errors)

    rmse = math.sqrt(
        statistics.mean(
            error ** 2
            for error in errors
        )
    )

    # ---------------------------------------------------------
    # Output reliability
    # ---------------------------------------------------------

    successful = len(rows)

    completion_rate = (
        successful / TOTAL_TEST_SAMPLES * 100
    )

    model_responses = (
        successful + invalid_attempts
    )

    valid_output_rate = (
        successful / model_responses * 100
        if model_responses
        else 0
    )

    total_attempts = (
        successful
        + invalid_attempts
        + api_errors
    )

    api_error_rate = (
        api_errors / total_attempts * 100
        if total_attempts
        else 0
    )

    # ---------------------------------------------------------
    # Fill bins
    # ---------------------------------------------------------

    bins = [
        ("0-19%", 0, 20),
        ("20-39%", 20, 40),
        ("40-59%", 40, 60),
        ("60-79%", 60, 80),
        ("80-100%", 80, 101),
    ]

    bin_results = []

    for label, low, high in bins:

        bin_errors = [
            safe_float(row["absolute_error"])
            for row in rows
            if low <= safe_float(row["ground_truth"]) < high
        ]

        if bin_errors:
            bin_results.append(
                (
                    label,
                    len(bin_errors),
                    statistics.mean(bin_errors)
                )
            )
        else:
            bin_results.append(
                (label, 0, None)
            )

    # ---------------------------------------------------------
    # Prediction distribution
    # ---------------------------------------------------------

    predictions = [
        safe_float(row["prediction"])
        for row in rows
    ]

    ground_truths = [
        safe_float(row["ground_truth"])
        for row in rows
    ]

    prediction_counts = Counter(predictions)

    unique_predictions = len(set(predictions))
    unique_gt = len(set(ground_truths))

    multiple_5 = sum(
        p % 5 == 0
        for p in predictions
    )

    multiple_10 = sum(
        p % 10 == 0
        for p in predictions
    )

    common_predictions = prediction_counts.most_common(10)

    # ---------------------------------------------------------
    # Report
    # ---------------------------------------------------------

    resolved_text = (
        ", ".join(sorted(resolved_models))
        if resolved_models
        else "Unknown"
    )

    report = []

    report.append("=" * 72)
    report.append("CRUSHER FILL-LEVEL ZERO-SHOT BENCHMARK REPORT")
    report.append("=" * 72)

    report.append("")
    report.append(f"Model alias          : {args.model}")
    report.append(f"Resolved model       : {resolved_text}")
    report.append("Evaluation mode      : Zero-shot")
    report.append("Lighting condition   : Night")
    report.append("Camera views/sample  : 2 (front_narrow + front_wide)")
    report.append(f"Frozen test samples  : {TOTAL_TEST_SAMPLES}")

    report.append("")
    report.append("1. OUTPUT RELIABILITY")
    report.append("-" * 72)

    report.append(
        f"Successful predictions : {successful}/{TOTAL_TEST_SAMPLES}"
    )

    report.append(
        f"Valid-prediction coverage: {completion_rate:.2f}%"
    )

    report.append(
        f"Valid-output rate      : {valid_output_rate:.2f}%"
    )

    report.append(
        f"Invalid outputs        : {invalid_attempts}"
    )

    report.append(
        f"API errors             : {api_errors}"
    )

    report.append(
        f"API error rate         : {api_error_rate:.2f}%"
    )

    report.append("")
    report.append("2. ACCURACY")
    report.append("-" * 72)

    report.append(
        f"MAE                    : {mae:.2f} percentage points"
    )

    report.append(
        f"Median Absolute Error  : {median_ae:.2f} percentage points"
    )

    report.append(
        f"RMSE                   : {rmse:.2f} percentage points"
    )

    report.append("")
    report.append("3. ERROR BY GROUND-TRUTH FILL RANGE")
    report.append("-" * 72)

    for label, count, value in bin_results:

        if value is None:
            report.append(
                f"{label:>8} : N/A (n={count})"
            )
        else:
            report.append(
                f"{label:>8} : {value:.2f} pp (n={count})"
            )

    report.append("")
    report.append("4. PREDICTION GRANULARITY")
    report.append("-" * 72)

    report.append(
        f"Unique ground-truth values : {unique_gt}"
    )

    report.append(
        f"Unique predicted values    : {unique_predictions}"
    )

    report.append(
        f"Predictions divisible by 5 : "
        f"{multiple_5}/{successful} "
        f"({100 * multiple_5 / successful:.1f}%)"
    )

    report.append(
        f"Predictions divisible by 10: "
        f"{multiple_10}/{successful} "
        f"({100 * multiple_10 / successful:.1f}%)"
    )

    report.append("")
    report.append("Most common predictions:")

    for prediction, count in common_predictions:

        report.append(
            f"  {prediction:>6.1f}% -> "
            f"{count:>3} samples "
            f"({100 * count / successful:>5.1f}%)"
        )

    report.append("")
    report.append("5. API USAGE")
    report.append("-" * 72)

    report.append(
        f"Total reported API cost : ${total_cost:.8f}"
    )

    report.append(
        f"Average cost/success    : "
        f"${total_cost / successful:.8f}"
    )

    report.append(
        f"Prompt tokens           : {prompt_tokens:,}"
    )

    report.append(
        f"Completion tokens       : {completion_tokens:,}"
    )

    report.append(
        f"Reasoning tokens        : {reasoning_tokens:,}"
    )

    report.append(
        f"Total tokens            : {total_tokens:,}"
    )

    report.append("")
    report.append("6. HUMAN-READABLE INTERPRETATION")
    report.append("-" * 72)

    report.append(
        f"The model achieved an MAE of {mae:.2f} percentage points "
        f"and an RMSE of {rmse:.2f} percentage points on the "
        f"{successful} valid numeric predictions from the frozen test set."
    )

    most_common_value, most_common_count = common_predictions[0]

    report.append("")
    report.append(
        f"The prediction distribution is concentrated: the test data "
        f"contains {unique_gt} distinct ground-truth values, while the "
        f"model produced {unique_predictions} distinct prediction values."
    )

    report.append("")
    report.append(
        f"The most frequent prediction was {most_common_value:.1f}%, "
        f"used for {most_common_count}/{successful} samples "
        f"({100 * most_common_count / successful:.1f}%)."
    )

    report.append("")
    report.append(
        "This indicates that the zero-shot model is producing relatively "
        "coarse numerical estimates rather than a finely calibrated "
        "continuous mapping from crusher appearance to fill percentage."
    )

    report.append("")
    report.append(
        "The fill-range results should be interpreted together with this "
        "prediction concentration. A low error within a particular range "
        "can partly occur when frequently produced predictions happen to "
        "fall inside that ground-truth range."
    )

    report.append("")
    report.append(
        "These observations describe this model on this benchmark only. "
        "Comparison with the other zero-shot VLMs is required before "
        "drawing conclusions about whether the same behavior is common "
        "across models."
    )

    report.append("")
    report.append("=" * 72)

    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    output_path = (
        REPORT_DIR
        / f"{args.model}_night_summary.txt"
    )

    output_path.write_text(
        "\n".join(report)
    )

    print("\n".join(report))

    print()
    print(
        f"Report saved to: {output_path}"
    )


if __name__ == "__main__":
    main()
