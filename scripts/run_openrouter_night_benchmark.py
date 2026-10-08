import argparse
import base64
import csv
import math
import os
import re
import sys
from pathlib import Path

import requests


# ============================================================
# PATHS
# ============================================================

WORKSPACE = Path("/workspace")

DATASET_ROOT = (
    WORKSPACE
    / "extracted"
    / "crusher_night_dataset_v1"
)

TEST_CSV = (
    DATASET_ROOT
    / "master_metadata.csv"
)

RESULTS_DIR = (
    WORKSPACE
    / "results"
    / "openrouter"
    / "full_benchmark"
)

OPENROUTER_URL = (
    "https://openrouter.ai/api/v1/chat/completions"
)

TOTAL_TEST_SAMPLES = 859


# ============================================================
# FIXED ZERO-SHOT PROMPT
#
# IMPORTANT:
# Keep this identical across models for the zero-shot test.
#
# The model is ONLY asked for the percentage.
# All evaluation metrics are calculated locally in Python.
# ============================================================

PROMPT = (
    "Estimate the fill level of the industrial crusher shown "
    "in the two images. "
    "Use visual information from both images. "
    "The fill level is a percentage from 0 to 100, where "
    "0 means completely empty and 100 means completely full. "
    "Return only the estimated percentage."
)


# ============================================================
# MODEL CONFIGURATION
#
# Same benchmark script for every model.
# Only the selected model changes.
# ============================================================

MODELS = {
    "qwen35_9b": "qwen/qwen3.5-9b",

    "qwen38_27b": "qwen/qwen3.8-27b",

    "deepseek_v41_flash": (
        "deepseek/deepseek-v4.1-flash"
    ),

    "kimi_k3": "moonshotai/kimi-k3",

    "glm_5v_turbo": "z-ai/glm-5v-turbo",

    "claude_fable_latest": (
        "~anthropic/claude-fable-latest"
    ),

    "claude_opus_latest": (
        "~anthropic/claude-opus-latest"
    ),

    "gpt_astra_latest": (
        "~openai/gpt-astra-latest"
    ),
}


# ============================================================
# PER-SAMPLE CSV FIELDS
# ============================================================

FIELDNAMES = [
    "eval_index",
    "recording_id",
    "sample",

    "ground_truth",
    "prediction",
    "absolute_error",

    "status",

    "requested_model",
    "resolved_model",

    "prompt_tokens",
    "completion_tokens",
    "reasoning_tokens",
    "total_tokens",

    "cost_usd",

    "narrow_image",
    "wide_image",

    "raw_output",
    "error_message",
]


# ============================================================
# ARGUMENTS
# ============================================================

def parse_args():

    parser = argparse.ArgumentParser(
        description=(
            "Safe OpenRouter zero-shot crusher benchmark."
        )
    )

    parser.add_argument(
        "--model",
        required=True,
        choices=sorted(MODELS.keys()),
        help="Model alias to evaluate.",
    )

    parser.add_argument(
        "--max-cost",
        type=float,
        default=1.0,
        help=(
            "Maximum reported NEW API cost in USD "
            "for this run."
        ),
    )

    parser.add_argument(
        "--max-samples",
        type=int,
        default=None,
        help=(
            "Maximum number of NEW API requests "
            "during this run."
        ),
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Validate everything without making "
            "any API requests."
        ),
    )

    return parser.parse_args()


# ============================================================
# IMAGE ENCODING
# ============================================================

def image_to_data_url(path: Path) -> str:

    with open(path, "rb") as f:
        encoded = base64.b64encode(
            f.read()
        ).decode("utf-8")

    suffix = path.suffix.lower()

    if suffix in [".jpg", ".jpeg"]:
        mime = "image/jpeg"

    elif suffix == ".png":
        mime = "image/png"

    else:
        raise ValueError(
            f"Unsupported image type: {path}"
        )

    return (
        f"data:{mime};base64,{encoded}"
    )


# ============================================================
# PERCENTAGE PARSER
# ============================================================

def parse_percentage(text):
    """
    Valid examples:

        63
        63%
        63.0%
        "63%"

    Requirements:

    - exactly one numeric value
    - value must be between 0 and 100

    This prevents explanations containing multiple numbers
    from silently becoming predictions.
    """

    if text is None:
        return None

    text = str(text).strip()

    matches = re.findall(
        r"-?\d+(?:\.\d+)?",
        text,
    )

    if len(matches) != 1:
        return None

    try:
        value = float(matches[0])

    except ValueError:
        return None

    if not 0.0 <= value <= 100.0:
        return None

    return value


# ============================================================
# LOAD FROZEN TEST SET
# ============================================================

def load_test_samples():

    if not TEST_CSV.exists():
        raise FileNotFoundError(
            f"Test metadata not found: {TEST_CSV}"
        )

    samples = []

    with open(
        TEST_CSV,
        newline="",
    ) as f:

        reader = csv.DictReader(f)

        for index, row in enumerate(
            reader,
            start=1,
        ):

            narrow_path = (
                DATASET_ROOT
                / row["front_narrow"]
            )

            wide_path = (
                DATASET_ROOT
                / row["front_wide"]
            )

            samples.append(
                {
                    "eval_index": index,

                    "recording_id":
                        row["recording_id"],

                    "sample":
                        row["sample"],

                    "ground_truth":
                        float(row["fill_level"]),

                    "narrow_path":
                        narrow_path,

                    "wide_path":
                        wide_path,
                }
            )

    return samples


# ============================================================
# RESUME SYSTEM
# ============================================================

def load_successful_samples(result_csv: Path):
    """
    Return eval_index values that already have at least one
    successful prediction.

    Example CSV history:

        183 -> api_error
        183 -> success

    Sample 183 is considered COMPLETE because a successful
    prediction exists.

    Therefore it will NOT be paid for again.
    """

    successful = set()

    if not result_csv.exists():
        return successful

    with open(
        result_csv,
        newline="",
    ) as f:

        reader = csv.DictReader(f)

        for row in reader:

            if row.get("status") in {
                "success",
                "invalid_output",
            }:

                try:
                    successful.add(
                        int(row["eval_index"])
                    )

                except (
                    ValueError,
                    TypeError,
                ):
                    pass

    return successful


# ============================================================
# IMMEDIATE RESULT SAVING
# ============================================================

def append_result(
    result_csv: Path,
    result: dict,
):
    """
    Save ONE API result immediately.

    flush + fsync reduces the chance that a completed paid
    request is lost if the process/server crashes.
    """

    result_csv.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    file_exists = result_csv.exists()

    with open(
        result_csv,
        "a",
        newline="",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=FIELDNAMES,
        )

        if not file_exists:
            writer.writeheader()

        writer.writerow(result)

        # Push Python buffer to OS.
        f.flush()

        # Ask OS to push data to disk.
        os.fsync(f.fileno())


# ============================================================
# OPENROUTER REQUEST
# ============================================================

def make_request(
    api_key,
    requested_model,
    narrow_path,
    wide_path,
):

    narrow_data = image_to_data_url(
        narrow_path
    )

    wide_data = image_to_data_url(
        wide_path
    )

    payload = {

        "model": requested_model,

        "temperature": 0,

        "max_tokens": 50,

        # Ask OpenRouter/provider not to use reasoning.
        # Some models/providers may ignore this.
        # Therefore actual reasoning usage is still logged.
        "reasoning": {
            "enabled": False
        },

        "messages": [
            {
                "role": "user",

                "content": [

                    # IMAGE 1
                    {
                        "type": "image_url",

                        "image_url": {
                            "url": narrow_data
                        },
                    },

                    # IMAGE 2
                    {
                        "type": "image_url",

                        "image_url": {
                            "url": wide_data
                        },
                    },

                    # PROMPT
                    {
                        "type": "text",
                        "text": PROMPT,
                    },
                ],
            }
        ],
    }

    headers = {

        "Authorization":
            f"Bearer {api_key}",

        "Content-Type":
            "application/json",
    }

    # IMPORTANT:
    # requests.post does NOT automatically retry here.
    #
    # One function call = one API attempt.
    response = requests.post(
        OPENROUTER_URL,
        headers=headers,
        json=payload,
        timeout=180,
    )

    if response.status_code != 200:

        raise RuntimeError(
            f"HTTP {response.status_code}: "
            f"{response.text[:1000]}"
        )

    return response.json()


# ============================================================
# TOKEN / COST EXTRACTION
# ============================================================

def extract_usage(response_json):

    usage = (
        response_json.get("usage")
        or {}
    )

    prompt_tokens = (
        usage.get(
            "prompt_tokens",
            0,
        )
        or 0
    )

    completion_tokens = (
        usage.get(
            "completion_tokens",
            0,
        )
        or 0
    )

    total_tokens = (
        usage.get(
            "total_tokens",
            0,
        )
        or 0
    )

    reasoning_tokens = 0

    details = (
        usage.get(
            "completion_tokens_details"
        )
        or {}
    )

    if isinstance(details, dict):

        reasoning_tokens = (
            details.get(
                "reasoning_tokens",
                0,
            )
            or 0
        )

    cost = (
        usage.get(
            "cost",
            0,
        )
        or 0
    )

    try:
        cost = float(cost)

    except (
        TypeError,
        ValueError,
    ):
        cost = 0.0

    return (
        prompt_tokens,
        completion_tokens,
        reasoning_tokens,
        total_tokens,
        cost,
    )


# ============================================================
# FINAL / CURRENT METRICS
# ============================================================

def calculate_metrics(result_csv: Path):
    """
    Calculate metrics from saved results.

    A sample can have multiple historical attempts:

        183 -> api_error
        183 -> success

    Accuracy metrics use each eval_index ONLY ONCE:
    its latest successful prediction.

    Cost/token totals include recorded API responses because
    failed/invalid responses may still have consumed resources.
    """

    if not result_csv.exists():

        print(
            "No result file exists yet."
        )

        return

    with open(
        result_csv,
        newline="",
    ) as f:

        reader = csv.DictReader(f)

        rows = list(reader)

    if not rows:

        print(
            "Result file is empty."
        )

        return


    # --------------------------------------------------------
    # Collect successful predictions
    # --------------------------------------------------------

    successful_by_index = {}

    api_error_attempts = 0

    invalid_output_attempts = 0


    # --------------------------------------------------------
    # API statistics
    # --------------------------------------------------------

    total_reported_cost = 0.0

    total_prompt_tokens = 0

    total_completion_tokens = 0

    total_reasoning_tokens = 0

    total_tokens = 0

    resolved_models = set()


    for row in rows:

        status = row.get(
            "status",
            "",
        )


        # ----------------------------------------------------
        # Failure counters
        # ----------------------------------------------------

        if status == "api_error":
            api_error_attempts += 1

        elif status == "invalid_output":
            invalid_output_attempts += 1


        # ----------------------------------------------------
        # Cost
        # ----------------------------------------------------

        try:
            total_reported_cost += float(
                row.get(
                    "cost_usd"
                )
                or 0
            )

        except (
            ValueError,
            TypeError,
        ):
            pass


        # ----------------------------------------------------
        # Prompt tokens
        # ----------------------------------------------------

        try:
            total_prompt_tokens += int(
                float(
                    row.get(
                        "prompt_tokens"
                    )
                    or 0
                )
            )

        except (
            ValueError,
            TypeError,
        ):
            pass


        # ----------------------------------------------------
        # Completion tokens
        # ----------------------------------------------------

        try:
            total_completion_tokens += int(
                float(
                    row.get(
                        "completion_tokens"
                    )
                    or 0
                )
            )

        except (
            ValueError,
            TypeError,
        ):
            pass


        # ----------------------------------------------------
        # Reasoning tokens
        # ----------------------------------------------------

        try:
            total_reasoning_tokens += int(
                float(
                    row.get(
                        "reasoning_tokens"
                    )
                    or 0
                )
            )

        except (
            ValueError,
            TypeError,
        ):
            pass


        # ----------------------------------------------------
        # Total tokens
        # ----------------------------------------------------

        try:
            total_tokens += int(
                float(
                    row.get(
                        "total_tokens"
                    )
                    or 0
                )
            )

        except (
            ValueError,
            TypeError,
        ):
            pass


        # ----------------------------------------------------
        # Resolved model/version
        # ----------------------------------------------------

        resolved_model = (
            row.get(
                "resolved_model",
                ""
            )
            .strip()
        )

        if resolved_model:
            resolved_models.add(
                resolved_model
            )


        # ----------------------------------------------------
        # Latest successful prediction
        # ----------------------------------------------------

        if status == "success":

            try:

                index = int(
                    row["eval_index"]
                )

                successful_by_index[
                    index
                ] = row

            except (
                ValueError,
                TypeError,
                KeyError,
            ):
                pass


    successful_rows = list(
        successful_by_index.values()
    )

    successful_count = len(
        successful_rows
    )


    # ========================================================
    # VALID OUTPUT RATE
    # ========================================================

    # --------------------------------------------------------
    # COMPLETION / OUTPUT RELIABILITY
    # --------------------------------------------------------
    
    # How much of the frozen 337-sample test set has a
    # successful final prediction.
    test_completion_rate = (
        successful_count
        / TOTAL_TEST_SAMPLES
        * 100
    )
    
    # Number of model responses that were actually received.
    # A valid prediction and an invalid_output both mean the
    # model returned something.
    model_responses = (
        successful_count
        + invalid_output_attempts
    )
    
    # Of the model responses received, how many produced a
    # valid parseable percentage?
    valid_output_rate = (
        successful_count
        / model_responses
        * 100
        if model_responses > 0
        else 0.0
    )
    
    # Total recorded attempts, including API failures.
    total_attempts = (
        successful_count
        + invalid_output_attempts
        + api_error_attempts
    )
    
    api_error_rate = (
        api_error_attempts
        / total_attempts
        * 100
        if total_attempts > 0
        else 0.0
    )


    print()

    print("=" * 70)

    print(
        "BENCHMARK SUMMARY"
    )

    print("=" * 70)


    if not successful_rows:

        print(
            "No successful predictions yet."
        )

        print(
            f"API error attempts      : "
            f"{api_error_attempts}"
        )

        print(
            f"Invalid output attempts : "
            f"{invalid_output_attempts}"
        )

        print(
            f"Reported API cost       : "
            f"${total_reported_cost:.8f}"
        )

        return


    # ========================================================
    # ACCURACY METRICS
    # ========================================================

    errors = [

        float(
            row["absolute_error"]
        )

        for row
        in successful_rows
    ]


    # --------------------------------------------------------
    # MAE
    # --------------------------------------------------------

    mae = (
        sum(errors)
        / len(errors)
    )


    # --------------------------------------------------------
    # RMSE
    # --------------------------------------------------------

    rmse = math.sqrt(

        sum(
            error ** 2
            for error
            in errors
        )

        / len(errors)
    )


    # --------------------------------------------------------
    # MEDIAN ABSOLUTE ERROR
    # --------------------------------------------------------

    errors_sorted = sorted(
        errors
    )

    n = len(
        errors_sorted
    )

    if n % 2 == 1:

        median_ae = (
            errors_sorted[
                n // 2
            ]
        )

    else:

        median_ae = (

            errors_sorted[
                n // 2 - 1
            ]

            +

            errors_sorted[
                n // 2
            ]

        ) / 2


    # ========================================================
    # FILL-RANGE / BIN-WISE MAE
    # ========================================================

    bins = {

        "0-19": [],

        "20-39": [],

        "40-59": [],

        "60-79": [],

        "80-100": [],
    }


    for row in successful_rows:

        gt = float(
            row["ground_truth"]
        )

        error = float(
            row["absolute_error"]
        )


        if 0 <= gt < 20:

            bins["0-19"].append(
                error
            )


        elif 20 <= gt < 40:

            bins["20-39"].append(
                error
            )


        elif 40 <= gt < 60:

            bins["40-59"].append(
                error
            )


        elif 60 <= gt < 80:

            bins["60-79"].append(
                error
            )


        elif 80 <= gt <= 100:

            bins["80-100"].append(
                error
            )


    # ========================================================
    # COST PER SUCCESSFUL SAMPLE
    # ========================================================

    if successful_count:

        average_cost_per_success = (

            total_reported_cost
            / successful_count
        )

    else:

        average_cost_per_success = 0.0


    # ========================================================
    # PRINT SUMMARY
    # ========================================================

    print()

    print(
        "DATASET / OUTPUT RELIABILITY"
    )

    print(
        "----------------------------"
    )

    print(
    f"Frozen test samples     : "
    f"{TOTAL_TEST_SAMPLES}"
    )

    print(
        f"Successful predictions  : "
        f"{successful_count}"
    )

    print(
        f"Test-set completion     : "
        f"{test_completion_rate:.2f}%"
    )

    print(
        f"Valid-output rate       : "
        f"{valid_output_rate:.2f}%"
    )

    print(
        f"Invalid output attempts : "
        f"{invalid_output_attempts}"
    )

    print(
        f"API error attempts      : "
        f"{api_error_attempts}"
    )

    print(
        f"API error rate          : "
        f"{api_error_rate:.2f}%"
    )


    print()

    print(
        "ACCURACY"
    )

    print(
        "--------"
    )

    print(
        f"MAE                     : "
        f"{mae:.2f} pp"
    )

    print(
        f"Median Absolute Error   : "
        f"{median_ae:.2f} pp"
    )

    print(
        f"RMSE                    : "
        f"{rmse:.2f} pp"
    )


    print()

    print(
        "FILL-RANGE MAE"
    )

    print(
        "--------------"
    )


    for name, values in bins.items():

        if values:

            bin_mae = (
                sum(values)
                / len(values)
            )

            print(

                f"{name:>6}% : "
                f"{bin_mae:.2f} pp "
                f"(n={len(values)})"
            )

        else:

            print(

                f"{name:>6}% : "
                f"N/A (n=0)"
            )


    print()

    print(
        "API COST"
    )

    print(
        "--------"
    )

    print(

        f"Total reported API cost : "
        f"${total_reported_cost:.8f}"
    )

    print(

        f"Avg cost / success      : "
        f"${average_cost_per_success:.8f}"
    )


    print()

    print(
        "TOKEN USAGE"
    )

    print(
        "-----------"
    )

    print(

        f"Prompt tokens           : "
        f"{total_prompt_tokens}"
    )

    print(

        f"Completion tokens       : "
        f"{total_completion_tokens}"
    )

    print(

        f"Reasoning tokens        : "
        f"{total_reasoning_tokens}"
    )

    print(

        f"Total tokens            : "
        f"{total_tokens}"
    )


    print()

    print(
        "MODEL VERSION"
    )

    print(
        "-------------"
    )

    if resolved_models:

        for model in sorted(
            resolved_models
        ):

            print(

                f"Resolved model          : "
                f"{model}"
            )

    else:

        print(
            "Resolved model          : unavailable"
        )


    print()

    print(
        "NOTE"
    )

    print(
        "----"
    )

    print(
        "Accuracy metrics use each eval_index once, "
        "using its latest successful prediction."
    )


# ============================================================
# MAIN BENCHMARK
# ============================================================

def main():

    args = parse_args()

    requested_model = (
        MODELS[
            args.model
        ]
    )

    result_csv = (

        RESULTS_DIR

        / f"{args.model}_night859.csv"
    )


    # ========================================================
    # HEADER
    # ========================================================

    print("=" * 70)

    print(
        "OPENROUTER CRUSHER ZERO-SHOT BENCHMARK"
    )

    print("=" * 70)


    print(
        f"Model alias     : "
        f"{args.model}"
    )

    print(
        f"Requested model : "
        f"{requested_model}"
    )

    print(
        f"Test metadata   : "
        f"{TEST_CSV}"
    )

    print(
        f"Results         : "
        f"{result_csv}"
    )

    print(
        f"Max NEW cost    : "
        f"${args.max_cost:.4f}"
    )

    print(
        f"Dry run         : "
        f"{args.dry_run}"
    )

    print()


    # ========================================================
    # LOAD DATASET
    # ========================================================

    samples = load_test_samples()

    print(
        f"Loaded test samples: "
        f"{len(samples)}"
    )


    # ========================================================
    # FROZEN TEST SET SAFETY CHECK
    # ========================================================

    if len(samples) != TOTAL_TEST_SAMPLES:

        print()

        print(
            "ERROR:"
        )

        print(
            f"Expected exactly "
            f"{TOTAL_TEST_SAMPLES} frozen test samples, "
            f"but found {len(samples)}."
        )

        print(
            "No API requests were made."
        )

        sys.exit(1)


    # ========================================================
    # VALIDATE ALL IMAGE FILES BEFORE PAYING
    # ========================================================

    missing_files = []


    for sample in samples:

        if not sample[
            "narrow_path"
        ].exists():

            missing_files.append(
                str(
                    sample[
                        "narrow_path"
                    ]
                )
            )


        if not sample[
            "wide_path"
        ].exists():

            missing_files.append(
                str(
                    sample[
                        "wide_path"
                    ]
                )
            )


    if missing_files:

        print()

        print(
            "ERROR: Missing image files."
        )

        for path in missing_files[:20]:

            print(path)

        print(
            f"Total missing files: "
            f"{len(missing_files)}"
        )

        print(
            "No API requests were made."
        )

        sys.exit(1)


    print(
        f"All "
        f"{TOTAL_TEST_SAMPLES * 2} "
        f"image files found."
    )


    # ========================================================
    # RESUME CHECK
    # ========================================================

    successful_samples = (
        load_successful_samples(
            result_csv
        )
    )


    print(

        f"Already completed successfully: "
        f"{len(successful_samples)}"
        f"/{TOTAL_TEST_SAMPLES}"
    )


    remaining = [

        sample

        for sample in samples

        if sample[
            "eval_index"
        ]

        not in successful_samples
    ]


    print(
        f"Remaining samples: "
        f"{len(remaining)}"
    )


    # ========================================================
    # DRY RUN
    # ========================================================

    if args.dry_run:

        print()

        print(
            "DRY RUN SUCCESSFUL"
        )

        print(
            "No API requests were made."
        )

        print()

        if remaining:

            sample = remaining[0]

            print(
                "First remaining sample:"
            )

            print(

                f"  Eval index : "
                f"{sample['eval_index']}"
            )

            print(

                f"  Recording  : "
                f"{sample['recording_id']}"
            )

            print(

                f"  Sample     : "
                f"{sample['sample']}"
            )

            print(

                f"  GT         : "
                f"{sample['ground_truth']}%"
            )

            print(

                f"  Narrow     : "
                f"{sample['narrow_path']}"
            )

            print(

                f"  Wide       : "
                f"{sample['wide_path']}"
            )

        else:

            print(
                "All test samples are already complete."
            )


        if result_csv.exists():

            calculate_metrics(
                result_csv
            )

        return


    # ========================================================
    # API KEY
    # ========================================================

    api_key = os.getenv(
        "OPENROUTER_API_KEY"
    )


    if not api_key:

        print()

        print(
            "ERROR:"
        )

        print(
            "OPENROUTER_API_KEY is not set."
        )

        print(
            "Do NOT paste the API key "
            "into this script."
        )

        sys.exit(1)


    # ========================================================
    # ALREADY COMPLETE?
    # ========================================================

    if not remaining:

        print()

        print(
            "All 337 samples are already completed."
        )

        calculate_metrics(
            result_csv
        )

        return


    # ========================================================
    # PAID MODE WARNING
    # ========================================================

    if args.max_samples is None:

        planned_requests = len(
            remaining
        )

    else:

        planned_requests = min(
            args.max_samples,
            len(remaining),
        )


    print()

    print("=" * 70)

    print(
        "WARNING: PAID API MODE"
    )

    print("=" * 70)

    print(

        f"This run can make up to "
        f"{planned_requests} NEW requests."
    )

    print(

        f"Configured NEW-run cost cutoff: "
        f"${args.max_cost:.4f}"
    )

    print()

    print(
        "Successful samples already saved "
        "will NOT be requested again."
    )

    print(
        "If an API request fails, the script "
        "will save the failure and STOP."
    )

    print(
        "There are NO automatic retries."
    )

    print()


    confirmation = input(
        "Type RUN to continue: "
    ).strip()


    if confirmation != "RUN":

        print()

        print(
            "Cancelled."
        )

        print(
            "No new API requests made."
        )

        return


    # ========================================================
    # RUN VARIABLES
    # ========================================================

    new_run_cost = 0.0

    new_requests = 0


    # ========================================================
    # SAMPLE LOOP
    # ========================================================

    for sample in remaining:


        # ----------------------------------------------------
        # MAX SAMPLE LIMIT
        # ----------------------------------------------------

        if (
            args.max_samples is not None

            and

            new_requests >= args.max_samples
        ):

            print()

            print(
                "Reached --max-samples limit."
            )

            break


        # ----------------------------------------------------
        # COST LIMIT
        #
        # Exact API cost is only known AFTER a request.
        # Therefore this prevents the NEXT request after the
        # reported cumulative cost reaches the configured
        # limit.
        # ----------------------------------------------------

        if new_run_cost >= args.max_cost:

            print()

            print(
                "Configured run-cost cutoff reached."
            )

            print(
                "No additional request will be made."
            )

            break


        print()

        print("-" * 70)

        print(

            f"[{sample['eval_index']}"
            f"/{TOTAL_TEST_SAMPLES}] "
            f"rec={sample['recording_id']} "
            f"sample={sample['sample']} "
            f"GT={sample['ground_truth']:.1f}%"
        )


        # ====================================================
        # EXACTLY ONE API ATTEMPT
        # ====================================================

        try:

            response_json = make_request(

                api_key=
                    api_key,

                requested_model=
                    requested_model,

                narrow_path=
                    sample["narrow_path"],

                wide_path=
                    sample["wide_path"],
            )


            # =================================================
            # RESOLVED MODEL
            # =================================================

            resolved_model = (
                response_json.get(
                    "model",
                    requested_model,
                )
            )


            # =================================================
            # MODEL OUTPUT
            # =================================================

            choices = (
                response_json.get(
                    "choices"
                )
                or []
            )


            if not choices:

                raise RuntimeError(
                    "API returned no choices."
                )


            message = (
                choices[0].get(
                    "message"
                )
                or {}
            )


            raw_output = (
                message.get(
                    "content"
                )
            )


            # =================================================
            # USAGE / COST
            # =================================================

            (
                prompt_tokens,
                completion_tokens,
                reasoning_tokens,
                total_tokens,
                cost,

            ) = extract_usage(
                response_json
            )


            # =================================================
            # PARSE PERCENTAGE
            # =================================================

            prediction = (
                parse_percentage(
                    raw_output
                )
            )


            # =================================================
            # INVALID MODEL OUTPUT
            # =================================================

            if prediction is None:


                result = {

                    "eval_index":
                        sample[
                            "eval_index"
                        ],

                    "recording_id":
                        sample[
                            "recording_id"
                        ],

                    "sample":
                        sample[
                            "sample"
                        ],

                    "ground_truth":
                        sample[
                            "ground_truth"
                        ],

                    "prediction":
                        "",

                    "absolute_error":
                        "",

                    "status":
                        "invalid_output",

                    "requested_model":
                        requested_model,

                    "resolved_model":
                        resolved_model,

                    "prompt_tokens":
                        prompt_tokens,

                    "completion_tokens":
                        completion_tokens,

                    "reasoning_tokens":
                        reasoning_tokens,

                    "total_tokens":
                        total_tokens,

                    "cost_usd":
                        cost,

                    "narrow_image":
                        str(
                            sample[
                                "narrow_path"
                            ]
                        ),

                    "wide_image":
                        str(
                            sample[
                                "wide_path"
                            ]
                        ),

                    "raw_output":
                        raw_output,

                    "error_message":
                        (
                            "Could not parse exactly "
                            "one percentage between "
                            "0 and 100."
                        ),
                }


                # SAVE IMMEDIATELY
                append_result(
                    result_csv,
                    result,
                )


                new_run_cost += cost

                new_requests += 1


                print(
                    f"INVALID OUTPUT: "
                    f"{raw_output!r}"
                )

                print(
                    f"Cost       : "
                    f"${cost:.8f}"
                )

                print(
                    "Failure saved to disk."
                )

                print(
                    "Invalid output recorded. Continuing to next sample."
                )

                continue


            # =================================================
            # SUCCESSFUL PREDICTION
            # =================================================

            absolute_error = abs(

                prediction

                -

                sample[
                    "ground_truth"
                ]
            )


            result = {

                "eval_index":
                    sample[
                        "eval_index"
                    ],

                "recording_id":
                    sample[
                        "recording_id"
                    ],

                "sample":
                    sample[
                        "sample"
                    ],

                "ground_truth":
                    sample[
                        "ground_truth"
                    ],

                "prediction":
                    prediction,

                "absolute_error":
                    absolute_error,

                "status":
                    "success",

                "requested_model":
                    requested_model,

                "resolved_model":
                    resolved_model,

                "prompt_tokens":
                    prompt_tokens,

                "completion_tokens":
                    completion_tokens,

                "reasoning_tokens":
                    reasoning_tokens,

                "total_tokens":
                    total_tokens,

                "cost_usd":
                    cost,

                "narrow_image":
                    str(
                        sample[
                            "narrow_path"
                        ]
                    ),

                "wide_image":
                    str(
                        sample[
                            "wide_path"
                        ]
                    ),

                "raw_output":
                    raw_output,

                "error_message":
                    "",
            }


            # =================================================
            # SAVE BEFORE DOING ANYTHING ELSE
            # =================================================

            append_result(
                result_csv,
                result,
            )


            new_run_cost += cost

            new_requests += 1


            print(
                f"Prediction : "
                f"{prediction:.1f}%"
            )

            print(
                f"Error      : "
                f"{absolute_error:.1f} pp"
            )

            print(
                f"Model      : "
                f"{resolved_model}"
            )

            print(
                f"Prompt tok : "
                f"{prompt_tokens}"
            )

            print(
                f"Output tok : "
                f"{completion_tokens}"
            )

            print(
                f"Reason tok : "
                f"{reasoning_tokens}"
            )

            print(
                f"Total tok  : "
                f"{total_tokens}"
            )

            print(
                f"Cost       : "
                f"${cost:.8f}"
            )

            print(
                f"Run cost   : "
                f"${new_run_cost:.8f}"
            )

            print(
                "Result saved ✓"
            )


        # ====================================================
        # API / NETWORK / OTHER FAILURE
        # ====================================================

        except Exception as exc:


            failure = {

                "eval_index":
                    sample[
                        "eval_index"
                    ],

                "recording_id":
                    sample[
                        "recording_id"
                    ],

                "sample":
                    sample[
                        "sample"
                    ],

                "ground_truth":
                    sample[
                        "ground_truth"
                    ],

                "prediction":
                    "",

                "absolute_error":
                    "",

                "status":
                    "api_error",

                "requested_model":
                    requested_model,

                "resolved_model":
                    "",

                "prompt_tokens":
                    "",

                "completion_tokens":
                    "",

                "reasoning_tokens":
                    "",

                "total_tokens":
                    "",

                "cost_usd":
                    "",

                "narrow_image":
                    str(
                        sample[
                            "narrow_path"
                        ]
                    ),

                "wide_image":
                    str(
                        sample[
                            "wide_path"
                        ]
                    ),

                "raw_output":
                    "",

                "error_message":
                    str(exc),
            }


            # SAVE FAILURE
            append_result(
                result_csv,
                failure,
            )


            print()

            print(
                "API ERROR"
            )

            print(
                str(exc)
            )

            print()

            print(
                "Failure information saved."
            )

            print(
                "Stopping immediately."
            )

            print(
                "NO automatic retry was attempted."
            )

            print()

            print(
                "When restarted, successful previous "
                "samples will be skipped and this "
                "unfinished sample can be attempted again."
            )

            break


    # ========================================================
    # RUN COMPLETE
    # ========================================================

    print()

    print("=" * 70)

    print(
        "RUN FINISHED"
    )

    print("=" * 70)

    print(

        f"New requests this run : "
        f"{new_requests}"
    )

    print(

        f"Reported new-run cost : "
        f"${new_run_cost:.8f}"
    )

    print(

        f"Results file          : "
        f"{result_csv}"
    )


    # ========================================================
    # CURRENT / FINAL METRICS
    # ========================================================

    calculate_metrics(
        result_csv
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()