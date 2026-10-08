from pathlib import Path
import json
import re

from PIL import Image
from transformers import pipeline


DATASET_DIR = Path(
    "/workspace/extracted/crusher_dataset_multicam"
)

TRAIN_JSONL = DATASET_DIR / "splits/train.jsonl"

MODEL_ID = "HuggingFaceTB/SmolVLM-256M-Instruct"


# --------------------------------------------------
# 1. Load train dataset
# --------------------------------------------------

with open(TRAIN_JSONL, "r") as f:
    train_samples = [json.loads(line) for line in f]

print(f"Train set contains {len(train_samples)} samples")


# --------------------------------------------------
# 2. Load pretrained SmolVLM
# --------------------------------------------------

print("Loading SmolVLM...")

pipe = pipeline(
    "image-text-to-text",
    model=MODEL_ID,
)


# --------------------------------------------------
# 3. Extract first numeric value from model output
# --------------------------------------------------

def extract_percentage(text):

    match = re.search(r"-?\d+(?:\.\d+)?", text)

    if match:
        return float(match.group())

    return None


# --------------------------------------------------
# 4. Evaluation variables
# --------------------------------------------------

errors = []

valid_predictions = 0
invalid_predictions = 0


print()
print("Running pretrained baseline on TRAIN set...")
print()


# --------------------------------------------------
# 5. Evaluate every train sample
# --------------------------------------------------

for sample in train_samples:

    sample_number = sample["metadata"]["sample"]

    ground_truth = float(
        sample["metadata"]["fill_level"]
    )

    narrow_path = (
        DATASET_DIR / sample["images"][0]
    )

    wide_path = (
        DATASET_DIR / sample["images"][1]
    )


    # Load both camera images
    narrow_image = Image.open(
        narrow_path
    ).convert("RGB")

    wide_image = Image.open(
        wide_path
    ).convert("RGB")


    # --------------------------------------------------
    # Same prompt used for test baseline
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
                    "text": (
                        "Estimate the fill level of the industrial crusher "
                        "shown in the two images. "
                        "Use visual information from both images. "
                        "The fill level is a percentage from 0 to 100, "
                        "where 0 means completely empty and 100 means "
                        "completely full. "
                        "Return only the estimated percentage."
                    ),
                },
            ],
        }
    ]


    # --------------------------------------------------
    # Run pretrained inference
    # --------------------------------------------------

    output = pipe(
        messages,
        max_new_tokens=20,
        return_full_text=False,
    )

    raw_output = output[0]["generated_text"]


    # --------------------------------------------------
    # Parse prediction
    # --------------------------------------------------

    prediction = extract_percentage(
        raw_output
    )


    # --------------------------------------------------
    # Validate prediction
    # --------------------------------------------------

    if (
        prediction is not None
        and 0 <= prediction <= 100
    ):

        error = abs(
            prediction - ground_truth
        )

        errors.append(error)

        valid_predictions += 1

        status = "VALID"

    else:

        error = None

        invalid_predictions += 1

        status = "INVALID"


    # --------------------------------------------------
    # Print result
    # --------------------------------------------------

    print(
        f"Sample {sample_number:03d} | "
        f"GT: {ground_truth:5.1f}% | "
        f"Output: {repr(raw_output)} | "
        f"Prediction: {prediction} | "
        f"Error: {error} | "
        f"{status}"
    )


# --------------------------------------------------
# 6. Final statistics
# --------------------------------------------------

print()
print("-----------------------------------")
print(f"Total train samples:   {len(train_samples)}")
print(f"Valid predictions:     {valid_predictions}")
print(f"Invalid predictions:   {invalid_predictions}")


if errors:

    mae = sum(errors) / len(errors)

    print(
        f"Pretrained Train MAE:  "
        f"{mae:.2f} percentage points"
    )

else:

    print(
        "Pretrained Train MAE:  unavailable"
    )