import os
import csv
import base64
import json
import re
import shutil
import urllib.request
import urllib.error
from pathlib import Path

# ============================================================
# SETTINGS
# ============================================================

MODEL = "qwen/qwen3.8-27b"

MAX_NEW_API_CALLS = 5
MAX_OUTPUT_TOKENS = 50

TARGET_LEVELS = [10, 30, 50, 70, 85]
TARGET_RECORDING = "39"

DATASET_ROOT = Path("/workspace/extracted/crusher_dataset_v2")
TEST_CSV = DATASET_ROOT / "splits" / "test_metadata.csv"

RESULTS_DIR = Path("/workspace/results/openrouter")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

STAGE2_CSV = RESULTS_DIR / "qwen3.8_27b_stage2_5samples.csv"
STAGE3_CSV = RESULTS_DIR / "qwen3.8_27b_stage3_10samples.csv"

PROMPT = (
    "Estimate the fill level of the industrial crusher shown in the two images. "
    "Use visual information from both images. "
    "The fill level is a percentage from 0 to 100, where 0 means completely empty "
    "and 100 means completely full. "
    "Return only the estimated percentage, for example: 63%"
)

# ============================================================
# API KEY
# ============================================================

api_key = os.getenv("OPENROUTER_API_KEY")

if not api_key:
    raise RuntimeError("OPENROUTER_API_KEY is not set.")


# ============================================================
# HELPERS
# ============================================================

def encode_image(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def parse_percentage(text):
    if text is None:
        return None

    match = re.search(r"(-?\d+(?:\.\d+)?)", text)

    if not match:
        return None

    value = float(match.group(1))

    if 0 <= value <= 100:
        return value

    return None


def load_results(path):
    if not path.exists():
        return []

    with open(path, newline="") as f:
        return list(csv.DictReader(f))


FIELDNAMES = [
    "evaluation_id",
    "recording_id",
    "sample",
    "ground_truth",
    "prediction",
    "absolute_error",
    "raw_output",
    "model_requested",
    "model_resolved",
    "prompt_tokens",
    "completion_tokens",
    "reasoning_tokens",
    "total_tokens",
    "cost_usd",
]


def write_results(rows):
    with open(STAGE3_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def append_result(row):
    exists = STAGE3_CSV.exists()

    with open(STAGE3_CSV, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)

        if not exists:
            writer.writeheader()

        writer.writerow(row)


# ============================================================
# IMPORT STAGE 2 RESULTS ON FIRST RUN
# ============================================================

if not STAGE3_CSV.exists():

    if not STAGE2_CSV.exists():
        raise FileNotFoundError(
            f"Stage 2 results not found: {STAGE2_CSV}"
        )

    stage2_rows = load_results(STAGE2_CSV)

    if len(stage2_rows) != 5:
        raise RuntimeError(
            f"Expected 5 Stage 2 results, found {len(stage2_rows)}"
        )

    converted = []

    for i, row in enumerate(stage2_rows, start=1):

        converted.append({
            "evaluation_id": i,
            "recording_id": row["recording_id"],
            "sample": row["sample"],
            "ground_truth": row["ground_truth"],
            "prediction": row["prediction"],
            "absolute_error": row["absolute_error"],
            "raw_output": row["raw_output"],
            "model_requested": row["model_requested"],
            "model_resolved": row["model_resolved"],
            "prompt_tokens": row["prompt_tokens"],
            "completion_tokens": row["completion_tokens"],
            "reasoning_tokens": row["reasoning_tokens"],
            "total_tokens": row["total_tokens"],
            "cost_usd": row["cost_usd"],
        })

    write_results(converted)

    print("Imported 5 completed Stage 2 results ✓")


# ============================================================
# LOAD TEST DATA
# ============================================================

with open(TEST_CSV, newline="") as f:
    all_test_rows = list(csv.DictReader(f))


recording39 = [
    row for row in all_test_rows
    if str(row["recording_id"]) == TARGET_RECORDING
]

if not recording39:
    raise RuntimeError(
        f"No test rows found for recording {TARGET_RECORDING}"
    )


# ============================================================
# SELECT 5 DIVERSE FILL LEVELS
# ============================================================

selected = []
used_samples = set()

for target in TARGET_LEVELS:

    candidates = [
        row for row in recording39
        if row["sample"] not in used_samples
    ]

    best = min(
        candidates,
        key=lambda row: abs(
            float(row["fill_level"]) - target
        )
    )

    selected.append({
        "target": target,
        "row": best
    })

    used_samples.add(best["sample"])


# ============================================================
# CHECK WHICH SELECTED SAMPLES ARE ALREADY COMPLETE
# ============================================================

existing_results = load_results(STAGE3_CSV)

existing_keys = {
    (str(row["recording_id"]), str(row["sample"]))
    for row in existing_results
}

remaining = []

for item in selected:
    row = item["row"]

    key = (
        str(row["recording_id"]),
        str(row["sample"])
    )

    if key not in existing_keys:
        remaining.append(item)


# ============================================================
# PRE-FLIGHT SUMMARY
# ============================================================

print()
print("=" * 76)
print("OPENROUTER STAGE 3 — TEN TOTAL SAMPLES")
print("=" * 76)

print(f"Model:                  {MODEL}")
print(f"Existing evaluations:   {len(existing_results)}")
print(f"New API calls required: {len(remaining)}")
print(f"MAX NEW API CALLS:      {MAX_NEW_API_CALLS}")
print(f"MAX OUTPUT TOKENS:      {MAX_OUTPUT_TOKENS}")
print("Reasoning:              DISABLED")

print()
print("Selected Stage 3 samples from recording 39:")
print()

for i, item in enumerate(selected, start=6):

    row = item["row"]

    print(
        f"Evaluation {i}: "
        f"target≈{item['target']}% | "
        f"sample={row['sample']} | "
        f"actual GT={float(row['fill_level']):.1f}%"
    )

print()
print("=" * 76)


# ============================================================
# HARD SAFETY CHECKS
# ============================================================

if len(remaining) > MAX_NEW_API_CALLS:
    raise RuntimeError(
        "SAFETY STOP: more than 5 new API calls would be required."
    )

if len(existing_results) > 10:
    raise RuntimeError(
        "SAFETY STOP: result file already contains more than 10 evaluations."
    )


# ============================================================
# RUN ONLY MISSING STAGE 3 SAMPLES
# ============================================================

for item in remaining:

    sample = item["row"]

    existing_results = load_results(STAGE3_CSV)

    evaluation_id = len(existing_results) + 1

    if evaluation_id > 10:
        raise RuntimeError(
            "SAFETY STOP: refusing to exceed 10 total evaluations."
        )

    narrow_path = DATASET_ROOT / sample["front_narrow"]
    wide_path = DATASET_ROOT / sample["front_wide"]

    ground_truth = float(sample["fill_level"])

    if not narrow_path.exists():
        raise FileNotFoundError(narrow_path)

    if not wide_path.exists():
        raise FileNotFoundError(wide_path)

    print()
    print("-" * 76)
    print(
        f"Evaluation {evaluation_id}/10 | "
        f"Recording {sample['recording_id']} | "
        f"Sample {sample['sample']}"
    )
    print(
        f"Target band ≈ {item['target']}% | "
        f"Ground truth = {ground_truth}%"
    )
    print("-" * 76)

    narrow_b64 = encode_image(narrow_path)
    wide_b64 = encode_image(wide_path)

    payload = {
        "model": MODEL,
        "temperature": 0,
        "max_tokens": MAX_OUTPUT_TOKENS,

        "reasoning": {
            "enabled": False
        },

        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{narrow_b64}"
                        }
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{wide_b64}"
                        }
                    },
                    {
                        "type": "text",
                        "text": PROMPT
                    }
                ]
            }
        ]
    }

    request = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        method="POST"
    )

    # ========================================================
    # EXACTLY ONE REQUEST FOR THIS SAMPLE
    # ========================================================

    try:

        with urllib.request.urlopen(
            request,
            timeout=120
        ) as response:

            result = json.loads(
                response.read().decode("utf-8")
            )

    except urllib.error.HTTPError as e:

        body = e.read().decode(
            "utf-8",
            errors="replace"
        )

        print("HTTP ERROR:", e.code)
        print(body)
        print()
        print("STOPPING — no automatic retry.")

        break

    except Exception as e:

        print(
            "REQUEST ERROR:",
            type(e).__name__,
            str(e)
        )

        print()
        print("STOPPING — no automatic retry.")

        break


    # ========================================================
    # PARSE RESPONSE
    # ========================================================

    message = result["choices"][0]["message"]

    raw_output = message.get("content")

    prediction = parse_percentage(raw_output)

    usage = result.get("usage", {}) or {}

    completion_details = usage.get(
        "completion_tokens_details",
        {}
    ) or {}

    reasoning_tokens = completion_details.get(
        "reasoning_tokens",
        0
    ) or 0

    if prediction is None:
        absolute_error = ""
    else:
        absolute_error = abs(
            prediction - ground_truth
        )

    result_row = {
        "evaluation_id": evaluation_id,
        "recording_id": sample["recording_id"],
        "sample": sample["sample"],
        "ground_truth": ground_truth,
        "prediction": (
            prediction
            if prediction is not None
            else ""
        ),
        "absolute_error": absolute_error,
        "raw_output": (
            raw_output
            if raw_output is not None
            else ""
        ),
        "model_requested": MODEL,
        "model_resolved": result.get(
            "model",
            "not returned"
        ),
        "prompt_tokens": usage.get(
            "prompt_tokens",
            0
        ),
        "completion_tokens": usage.get(
            "completion_tokens",
            0
        ),
        "reasoning_tokens": reasoning_tokens,
        "total_tokens": usage.get(
            "total_tokens",
            0
        ),
        "cost_usd": usage.get(
            "cost",
            0
        ) or 0,
    }

    append_result(result_row)

    print("Raw output:       ", repr(raw_output))
    print("Parsed prediction:", prediction)
    print("Ground truth:     ", ground_truth)
    print("Absolute error:   ", absolute_error)
    print("Reasoning tokens: ", reasoning_tokens)
    print("Cost:             ", result_row["cost_usd"])


# ============================================================
# FINAL SUMMARY
# ============================================================

final_results = load_results(STAGE3_CSV)

errors = []
costs = []

for row in final_results:

    if row["prediction"] != "":
        prediction = float(row["prediction"])
        ground_truth = float(row["ground_truth"])

        errors.append(
            abs(prediction - ground_truth)
        )

    try:
        costs.append(
            float(row["cost_usd"])
        )
    except Exception:
        pass


print()
print("=" * 76)
print("STAGE 3 SUMMARY")
print("=" * 76)

print(f"Completed evaluations: {len(final_results)}/10")
print(f"Valid predictions:     {len(errors)}")

if errors:

    mae = sum(errors) / len(errors)

    print(
        f"MAE:                   "
        f"{mae:.2f} percentage points"
    )

else:
    print("MAE:                   unavailable")

total_cost = sum(costs)

print(
    f"Total cumulative cost: ${total_cost:.6f}"
)

if len(final_results) > 0:

    avg_cost = total_cost / len(final_results)

    print(
        f"Average cost/sample:    ${avg_cost:.6f}"
    )

    estimated_337 = avg_cost * 337

    print(
        f"Rough 337-sample cost:  ${estimated_337:.2f}"
    )

print()
print("Results saved to:")
print(STAGE3_CSV)

print("=" * 76)
