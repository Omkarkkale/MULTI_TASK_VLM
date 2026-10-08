import os
import csv
import base64
import json
import re
import time
import urllib.request
import urllib.error
from pathlib import Path

# ============================================================
# SAFETY SETTINGS
# ============================================================

MAX_CALLS_PER_MODEL = 1
MAX_OUTPUT_TOKENS = 50

DATASET_ROOT = Path("/workspace/extracted/crusher_dataset_v2")
TEST_CSV = DATASET_ROOT / "splits" / "test_metadata.csv"

RESULTS_DIR = Path("/workspace/results/openrouter")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

RESULTS_CSV = RESULTS_DIR / "all_models_one_sample.csv"

PROMPT = (
    "Estimate the fill level of the industrial crusher shown in the two images. "
    "Use visual information from both images. "
    "The fill level is a percentage from 0 to 100, where 0 means completely empty "
    "and 100 means completely full. "
    "Return only the estimated percentage, for example: 63%"
)

# ============================================================
# MODELS
# ============================================================

MODELS = [
    {
        "name": "Claude Fable Latest",
        "id": "~anthropic/claude-fable-latest",
    },
    {
        "name": "Claude Opus Latest",
        "id": "~anthropic/claude-opus-latest",
    },
    {
        "name": "GPT Astra Latest",
        "id": "~openai/gpt-astra-latest",
    },
    {
        "name": "Qwen3.8 2.4T A95B",
        "id": "qwen/qwen3.8-2.4t-a95b",
    },
    {
        "name": "Qwen3.8 27B",
        "id": "qwen/qwen3.8-27b",
    },
    {
        "name": "Qwen3.5 9B",
        "id": "qwen/qwen3.5-9b",
    },
    {
        "name": "DeepSeek V4.1 Flash",
        "id": "deepseek/deepseek-v4.1-flash",
    },
    {
        "name": "Kimi K3",
        "id": "moonshotai/kimi-k3",
    },
    {
        "name": "GLM 5V Turbo",
        "id": "z-ai/glm-5v-turbo",
    },
]

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
    if not text:
        return None

    match = re.search(r"(-?\d+(?:\.\d+)?)", text)

    if not match:
        return None

    value = float(match.group(1))

    if 0 <= value <= 100:
        return value

    return None


FIELDNAMES = [
    "model_name",
    "model_requested",
    "model_resolved",
    "recording_id",
    "sample",
    "ground_truth",
    "prediction",
    "absolute_error",
    "raw_output",
    "status",
    "prompt_tokens",
    "completion_tokens",
    "reasoning_tokens",
    "total_tokens",
    "cost_usd",
    "estimated_337_cost_usd",
]


def load_existing():
    if not RESULTS_CSV.exists():
        return {}

    results = {}

    with open(RESULTS_CSV, newline="") as f:
        reader = csv.DictReader(f)

        for row in reader:
            results[row["model_requested"]] = row

    return results


def append_result(row):
    exists = RESULTS_CSV.exists()

    with open(RESULTS_CSV, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)

        if not exists:
            writer.writeheader()

        writer.writerow(row)


# ============================================================
# LOAD EXACTLY ONE TEST SAMPLE
# ============================================================

with open(TEST_CSV, newline="") as f:
    reader = csv.DictReader(f)
    sample = next(reader)

narrow_path = DATASET_ROOT / sample["front_narrow"]
wide_path = DATASET_ROOT / sample["front_wide"]

if not narrow_path.exists():
    raise FileNotFoundError(narrow_path)

if not wide_path.exists():
    raise FileNotFoundError(wide_path)

ground_truth = float(sample["fill_level"])

narrow_b64 = encode_image(narrow_path)
wide_b64 = encode_image(wide_path)

# ============================================================
# PRE-FLIGHT
# ============================================================

existing = load_existing()

remaining_models = [
    m for m in MODELS
    if m["id"] not in existing
]

print("=" * 80)
print("OPENROUTER MULTI-MODEL ONE-SAMPLE COMPATIBILITY TEST")
print("=" * 80)

print(f"Recording:             {sample['recording_id']}")
print(f"Sample:                {sample['sample']}")
print(f"Ground truth:          {ground_truth}%")
print(f"Number of models:      {len(MODELS)}")
print(f"Already completed:     {len(existing)}")
print(f"New API calls needed:  {len(remaining_models)}")
print(f"Max calls/model:       {MAX_CALLS_PER_MODEL}")
print(f"Max output tokens:     {MAX_OUTPUT_TOKENS}")
print()
print("Each model receives the SAME two images and SAME prompt.")
print("=" * 80)

if len(remaining_models) > len(MODELS):
    raise RuntimeError("SAFETY STOP: unexpected model count.")

# ============================================================
# RUN
# ============================================================

for index, model in enumerate(remaining_models, start=1):

    model_name = model["name"]
    model_id = model["id"]

    print()
    print("-" * 80)
    print(f"[{index}/{len(remaining_models)}] {model_name}")
    print(f"Requested ID: {model_id}")
    print("-" * 80)

    payload = {
        "model": model_id,
        "temperature": 0,
        "max_tokens": MAX_OUTPUT_TOKENS,

        # For models supporting controllable reasoning,
        # disable it for this simple visual regression task.
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

    try:
        with urllib.request.urlopen(
            request,
            timeout=180
        ) as response:

            result = json.loads(
                response.read().decode("utf-8")
            )

    except urllib.error.HTTPError as e:

        error_body = e.read().decode(
            "utf-8",
            errors="replace"
        )

        print(f"FAILED: HTTP {e.code}")
        print(error_body[:1000])

        append_result({
            "model_name": model_name,
            "model_requested": model_id,
            "model_resolved": "",
            "recording_id": sample["recording_id"],
            "sample": sample["sample"],
            "ground_truth": ground_truth,
            "prediction": "",
            "absolute_error": "",
            "raw_output": error_body[:1000],
            "status": f"HTTP_ERROR_{e.code}",
            "prompt_tokens": "",
            "completion_tokens": "",
            "reasoning_tokens": "",
            "total_tokens": "",
            "cost_usd": "",
            "estimated_337_cost_usd": "",
        })

        continue

    except Exception as e:

        print(
            "FAILED:",
            type(e).__name__,
            str(e)
        )

        append_result({
            "model_name": model_name,
            "model_requested": model_id,
            "model_resolved": "",
            "recording_id": sample["recording_id"],
            "sample": sample["sample"],
            "ground_truth": ground_truth,
            "prediction": "",
            "absolute_error": "",
            "raw_output": str(e),
            "status": "REQUEST_ERROR",
            "prompt_tokens": "",
            "completion_tokens": "",
            "reasoning_tokens": "",
            "total_tokens": "",
            "cost_usd": "",
            "estimated_337_cost_usd": "",
        })

        continue

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

    cost = usage.get("cost", 0) or 0

    resolved_model = result.get(
        "model",
        "not returned"
    )

    if prediction is None:
        status = "INVALID_OUTPUT"
        absolute_error = ""
    else:
        status = "OK"
        absolute_error = abs(
            prediction - ground_truth
        )

    estimated_337_cost = (
        float(cost) * 337
        if cost not in (None, "")
        else ""
    )

    append_result({
        "model_name": model_name,
        "model_requested": model_id,
        "model_resolved": resolved_model,
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
        "status": status,
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
        "cost_usd": cost,
        "estimated_337_cost_usd": estimated_337_cost,
    })

    print("Status:             ", status)
    print("Raw output:         ", repr(raw_output))
    print("Prediction:         ", prediction)
    print("Ground truth:       ", ground_truth)
    print("Absolute error:     ", absolute_error)
    print("Resolved model:     ", resolved_model)
    print("Prompt tokens:      ", usage.get("prompt_tokens", 0))
    print("Completion tokens:  ", usage.get("completion_tokens", 0))
    print("Reasoning tokens:   ", reasoning_tokens)
    print("Cost:               ", cost)
    print(
        "337-sample estimate:",
        f"${estimated_337_cost:.4f}"
    )

    # Tiny pause, not a retry.
    time.sleep(1)


# ============================================================
# FINAL SUMMARY
# ============================================================

final_results = load_existing()

print()
print("=" * 80)
print("COMPATIBILITY TEST SUMMARY")
print("=" * 80)

total_estimated_337_cost = 0.0
successful = 0

for model in MODELS:

    row = final_results.get(model["id"])

    if not row:
        print(
            f"{model['name']:<25} | NOT RUN"
        )
        continue

    status = row["status"]
    prediction = row["prediction"]
    cost = row["cost_usd"]
    projected = row["estimated_337_cost_usd"]
    resolved = row["model_resolved"]

    if status == "OK":
        successful += 1

    if projected not in ("", None):
        try:
            total_estimated_337_cost += float(projected)
        except Exception:
            pass

    print(
        f"{model['name']:<25} | "
        f"{status:<15} | "
        f"Pred={prediction or '-':<6} | "
        f"Cost=${cost or '-'}"
    )

print()
print(
    f"Successful models: {successful}/{len(MODELS)}"
)

print(
    "Rough combined 337-sample estimate: "
    f"${total_estimated_337_cost:.2f}"
)

print()
print("NOTE:")
print(
    "The 337-sample estimate is based on ONE sample per model, "
    "so it is only a preliminary estimate."
)

print()
print("Results saved to:")
print(RESULTS_CSV)

print("=" * 80)
