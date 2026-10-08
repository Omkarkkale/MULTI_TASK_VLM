from pathlib import Path
import json

from PIL import Image
from transformers import pipeline


DATASET_DIR = Path(
    "/workspace/extracted/crusher_dataset_multicam"
)

JSONL_PATH = (
    DATASET_DIR / "smolvlm_multicam_dataset.jsonl"
)


# --------------------------------------------------
# 1. Read first dataset sample
# --------------------------------------------------

with open(JSONL_PATH, "r") as f:
    sample = json.loads(f.readline())


print("Sample loaded:")
print(sample)


# --------------------------------------------------
# 2. Open both images using PIL
# --------------------------------------------------

narrow_path = DATASET_DIR / sample["images"][0]
wide_path = DATASET_DIR / sample["images"][1]

narrow_image = Image.open(narrow_path).convert("RGB")
wide_image = Image.open(wide_path).convert("RGB")


print()
print("Images loaded:")
print("Narrow:", narrow_image.size)
print("Wide:", wide_image.size)


# --------------------------------------------------
# 3. Create SmolVLM pipeline
# --------------------------------------------------

print()
print("Loading SmolVLM...")

pipe = pipeline(
    "image-text-to-text",
    model="HuggingFaceTB/SmolVLM-256M-Instruct",
)


# --------------------------------------------------
# 4. Prepare prompt
# --------------------------------------------------

messages = [
    {
        "role": "user",
        "content": [
            {
                "type": "image",
                "image": narrow_image,
            },
            {
                "type": "image",
                "image": wide_image,
            },
            {
                "type": "text",
                "text": "What is the crusher fill level? Answer only with a percentage.",
            },
        ],
    }
]

print()
print("Running inference...")

output = pipe(
    messages,
    max_new_tokens=20,
    return_full_text=False,
)

# --------------------------------------------------
# 6. Print result
# --------------------------------------------------

ground_truth = sample["messages"][1]["content"][0]["text"]

print()
print("Ground truth:", ground_truth)
print("Model output:", output[0]["generated_text"])