import os
import csv
import base64
import json
import re
import urllib.request
import urllib.error
from pathlib import Path

# ============================================================
# SETTINGS
# ============================================================

MODEL = "qwen/qwen3.8-27b"
TARGET_TOTAL_SAMPLES = 5
MAX_OUTPUT_TOKENS = 50

DATASET_ROOT = Path("/workspace/extracted/crusher_dataset_v2")
TEST_CSV = DATASET_ROOT / "splits" / "test_metadata.csv"

RESULTS_DIR = Path("/workspace/results/openrouter")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

RESULTS_CSV = RESULTS_DIR / "qwen3.8_27b_stage2_5samples.csv"

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
    """
    Extract first numeric percentage from model output.

    Examples:
        '75%'       -> 75.0
        '75'        -> 75.0
        '75.5%'     -> 75.5
        'about 75%' -> 75.0
    """
    if text is None:
        return None

    match = re.search(r"(-?\d+(?:\.\d+)?)", text)

    if not match:
        return None

    value = float(match.group(1))

    if 0 <= value <= 100:
        return value

    return None


def load_existing_results():
    if not RESULTS_CSV.exists():
        return {}

    results = {}

    with open(RESULTS_CSV, newline="") as f:
        reader = csv.DictReader(f)

        for row in reader:
            results[int(row["test_index"])] = row

    return results


def append_result(row):
    file_exists = RESULTS_CSV.exists()

    fieldnames = [
        "test_index",
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

    with open(RESULTS_CSV, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        if not file_exists:
            writer.writeheader()

        writer.writerow(row)


# ============================================================
# LOAD FIRST 5 TEST SAMPLES
# ============================================================

with open(TEST_CSV, newline="") as f:
    reader = csv.DictReader(f)
    samples = []

    for i, row in enumerate(reader, start=1):
        samples.append(row)

        if i >= TARGET_TOTAL_SAMPLES:
            break

if len(samples) != TARGET_TOTAL_SAMPLES:
    raise RuntimeError(
        f"Expected {TARGET_TOTAL_SAMPLES} test samples, found {len(samples)}."
    )


# ============================================================
# SEED PREVIOUSLY COMPLETED SAMPLE 1
# ============================================================

existing = load_existing_results()

if 1 not in existing:
    sample1 = samples[0]
    gt1 = float(sample1["fill_level"])

    # Result already obtained during successful one-sample smoke test:
    # prediction 75%, GT 100%, cost $0.00134152
    seeded_row = {
        "test_index": 1,
        "recording_id": sample1["recording_id"],
        "sample": sample1["sample"],
        "ground_truth": gt1,
        "prediction": 75.0,
        "absolute_error": abs(75.0 - gt1),
        "raw_output": "75%",
        "model_requested": MODEL,
        "model_resolved": "qwen/qwen3.8-27b",
        "prompt_tokens": 4161,
        "completion_tokens": 4,
        "reasoning_tokens": 0,
        "total_tokens": 4165,
        "cost_usd": 0.00134152,
    }

    append_result(seeded_row)

    print("Seeded already-completed sample 1 ✓")

existing = load_existing_results()


# ============================================================
# SAFETY SUMMARY
# ============================================================

completed = sorted(existing.keys())
remaining = [
    i for i in range(1, TARGET_TOTAL_SAMPLES + 1)
    if i not in existing
]

print("=" * 72)
print("OPENROUTER STAGE 2 — FIVE TOTAL SAMPLES")
print("=" * 72)

print("Model:                 ", MODEL)
print("Target total samples:  ", TARGET_TOTAL_SAMPLES)
print("Already completed:     ", completed)
print("New API calls required:", len(remaining))
print("Samples to call:       ", remaining)
print("Max output tokens:     ", MAX_OUTPUT_TOKENS)
print("Reasoning:              DISABLED")
print("Results file:          ", RESULTS_CSV)

print("=" * 72)

# Hard safety check
if len(remaining) > 4:
    raise RuntimeError(
        "SAFETY STOP: Stage 2 must make no more than 4 new API calls."
    )


# ============================================================
# RUN ONLY MISSING SAMPLES
# ============================================================

for test_index in remaining:

    sample = samples[test_index - 1]

    narrow_path = DATASET_ROOT / sample["front_narrow"]
    wide_path = DATASET_ROOT / sample["front_wide"]

    ground_truth = float(sample["fill_level"])

    if not narrow_path.exists():
        raise FileNotFoundError(narrow_path)

    if not wide_path.exists():
        raise FileNotFoundError(wide_path)

    print()
    print("-" * 72)
    print(
        f"Evaluating test sample {test_index}/{TARGET_TOTAL_SAMPLES}"
    )
    print(
        f"Recording {sample['recording_id']} | "
        f"sample {sample['sample']} | "
        f"GT {ground_truth}%"
    )
    print("-" * 72)

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
        body = e.read().decode("utf-8", errors="replace")

        print("HTTP ERROR:", e.code)
        print(body)

        print()
        print("STOPPING — no automatic retry.")
        break

    except Exception as e:
        print("REQUEST ERROR:", type(e).__name__, str(e))
        print()
        print("STOPPING — no automatic retry.")
        break

    # ========================================================
    # PARSE RESULT
    # ========================================================

    message = result["choices"][0]["message"]

    raw_output = message.get("content")
    prediction = parse_percentage(raw_output)

    usage = result.get("usage", {})

    prompt_tokens = usage.get("prompt_tokens", 0)
    completion_tokens = usage.get("completion_tokens", 0)
    total_tokens = usage.get("total_tokens", 0)
    cost = usage.get("cost", 0) or 0

    completion_details = usage.get(
        "completion_tokens_details",
        {}
    ) or {}

    reasoning_tokens = completion_details.get(
        "reasoning_tokens",
        0
    ) or 0

    resolved_model = result.get(
        "model",
        "not returned"
    )

    if prediction is None:
        absolute_error = ""
    else:
        absolute_error = abs(
            prediction - ground_truth
        )

    row = {
        "test_index": test_index,
        "recording_id": sample["recording_id"],
        "sample": sample["sample"],
        "ground_truth": ground_truth,
        "prediction": (
            prediction
            if prediction is not None
            else ""
        ),
        "absolute_error": absolute_error,
        "raw_output": raw_output,
        "model_requested": MODEL,
        "model_resolved": resolved_model,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "reasoning_tokens": reasoning_tokens,
        "total_tokens": total_tokens,
        "cost_usd": cost,
    }

    append_result(row)

    print("Raw output:      ", repr(raw_output))
    print("Parsed prediction:", prediction)
    print("Ground truth:    ", ground_truth)
    print("Absolute error:  ", absolute_error)
    print("Reasoning tokens:", reasoning_tokens)
    print("Cost:            ", cost)

    # Critical:
    # Update cache immediately after every successful request.
    existing = load_existing_results()


# ============================================================
# FINAL SUMMARY
# ============================================================

final_results = load_existing_results()

valid_predictions = []
costs = []

for i in sorted(final_results):

    if i > TARGET_TOTAL_SAMPLES:
        continue

    row = final_results[i]

    pred_text = row["prediction"]
    gt_text = row["ground_truth"]

    if pred_text != "":
        pred = float(pred_text)
        gt = float(gt_text)

        valid_predictions.append(
            abs(pred - gt)
        )

    try:
        costs.append(
            float(row["cost_usd"])
        )
    except Exception:
        pass


print()
print("=" * 72)
print("STAGE 2 SUMMARY")
print("=" * 72)

print(
    f"Completed: "
    f"{len([i for i in final_results if i <= TARGET_TOTAL_SAMPLES])}"
    f"/{TARGET_TOTAL_SAMPLES}"
)

if valid_predictions:
    mae = sum(valid_predictions) / len(valid_predictions)

    print(
        f"Valid predictions: {len(valid_predictions)}"
    )

    print(
        f"MAE:               {mae:.2f} percentage points"
    )

else:
    print("Valid predictions: 0")
    print("MAE:               unavailable")

print(
    f"Total recorded cost: ${sum(costs):.6f}"
)

print()
print("Results saved to:")
print(RESULTS_CSV)

print("=" * 72)
