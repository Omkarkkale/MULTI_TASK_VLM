from pathlib import Path
import json

DATASET_DIR = Path(
    "/workspace/extracted/crusher_dataset_multicam"
)

JSONL_PATH = (
    DATASET_DIR / "smolvlm_multicam_dataset.jsonl"
)

total = 0
bad_samples = 0
missing_images = 0


with open(JSONL_PATH, "r") as f:

    for line_number, line in enumerate(f, start=1):

        total += 1

        try:
            sample = json.loads(line)
        except json.JSONDecodeError:
            print(f"Line {line_number}: invalid JSON")
            bad_samples += 1
            continue

        # Check images field
        images = sample.get("images")

        if not isinstance(images, list) or len(images) != 2:
            print(
                f"Line {line_number}: expected exactly 2 images"
            )
            bad_samples += 1
            continue

        # Check both image files exist
        for image_path in images:

            full_path = DATASET_DIR / image_path

            if not full_path.exists():
                print(
                    f"Line {line_number}: "
                    f"missing image {full_path}"
                )
                missing_images += 1

        # Check messages
        messages = sample.get("messages")

        if not isinstance(messages, list) or len(messages) != 2:
            print(
                f"Line {line_number}: invalid messages"
            )
            bad_samples += 1
            continue

        user_message = messages[0]
        assistant_message = messages[1]

        if user_message.get("role") != "user":
            print(
                f"Line {line_number}: "
                f"first message is not user"
            )
            bad_samples += 1

        if assistant_message.get("role") != "assistant":
            print(
                f"Line {line_number}: "
                f"second message is not assistant"
            )
            bad_samples += 1


print()
print("Validation complete.")
print(f"Total samples:   {total}")
print(f"Missing images:  {missing_images}")
print(f"Bad samples:     {bad_samples}")