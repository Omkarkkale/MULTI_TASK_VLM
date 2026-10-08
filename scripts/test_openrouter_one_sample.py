import os
import csv
import base64
import json
import urllib.request
from pathlib import Path

# ============================================================
# HARD SAFETY SETTINGS
# ============================================================

MAX_SAMPLES = 1
MODEL = "qwen/qwen3.8-27b"
MAX_OUTPUT_TOKENS = 50

DATASET_ROOT = Path("/workspace/extracted/crusher_dataset_v2")
TEST_CSV = DATASET_ROOT / "splits" / "test_metadata.csv"

PROMPT = (
    "Estimate the fill level of the industrial crusher shown in the two images. "
    "Use visual information from both images. "
    "The fill level is a percentage from 0 to 100, where 0 means completely empty "
    "and 100 means completely full. "
    "Return only the estimated percentage, for example: 63%"
)

# ============================================================
# SAFETY CHECKS
# ============================================================

api_key = os.getenv("OPENROUTER_API_KEY")

if not api_key:
    raise RuntimeError("OPENROUTER_API_KEY is not set.")

if MAX_SAMPLES != 1:
    raise RuntimeError(
        "SAFETY STOP: this script must run exactly one sample."
    )


def encode_image(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


# ============================================================
# LOAD EXACTLY ONE SAMPLE
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


# ============================================================
# DISPLAY BEFORE API CALL
# ============================================================

print("=" * 70)
print("OPENROUTER ONE-SAMPLE SAFETY TEST")
print("=" * 70)

print(f"Model:             {MODEL}")
print(f"Recording:         {sample['recording_id']}")
print(f"Sample:            {sample['sample']}")
print(f"Ground truth:      {ground_truth}%")
print(f"Narrow image:      {narrow_path}")
print(f"Wide image:        {wide_path}")

print()
print("MAX API CALLS:     1")
print(f"MAX OUTPUT TOKENS: {MAX_OUTPUT_TOKENS}")
print("REASONING:         DISABLED")
print("=" * 70)


# ============================================================
# ENCODE IMAGES
# ============================================================

narrow_b64 = encode_image(narrow_path)
wide_b64 = encode_image(wide_path)


# ============================================================
# OPENROUTER REQUEST
# ============================================================

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


print()
print("About to make EXACTLY ONE paid API request...")
print()


# ============================================================
# MAKE EXACTLY ONE REQUEST
# ============================================================

try:
    with urllib.request.urlopen(request, timeout=120) as response:
        result = json.loads(response.read().decode("utf-8"))

except Exception as e:
    print("=" * 70)
    print("API REQUEST FAILED")
    print("=" * 70)
    print(type(e).__name__, str(e))
    raise


# ============================================================
# RESULTS
# ============================================================

print("=" * 70)
print("RESULT")
print("=" * 70)

message = result["choices"][0]["message"]
prediction_text = message.get("content")

print("Raw model output:", repr(prediction_text))
print("Ground truth:    ", ground_truth)


if prediction_text is None:
    print()
    print("WARNING: No visible answer returned.")
    print("Complete model message:")
    print(json.dumps(message, indent=2))


# ============================================================
# TOKEN / COST INFORMATION
# ============================================================

usage = result.get("usage", {})

print()
print("Usage returned by OpenRouter:")
print(json.dumps(usage, indent=2))

print()
print("Resolved model:", result.get("model", "not returned"))

print()
print("STOPPED AFTER EXACTLY 1 REQUEST ✓")
print("=" * 70)
