import json
import os


dataset_file = "/workspace/extracted/crusher_dataset/smolvlm_dataset.jsonl"
dataset_dir = "/workspace/extracted/crusher_dataset"


total = 0
missing_images = 0
bad_samples = 0


with open(dataset_file, "r") as f:

    for line_number, line in enumerate(f, start=1):

        total += 1

        try:
            sample = json.loads(line)
        except json.JSONDecodeError:
            print(f"Invalid JSON at line {line_number}")
            bad_samples += 1
            continue

        image_path = os.path.join(
            dataset_dir,
            sample["image"]
        )

        if not os.path.exists(image_path):
            print(
                f"Missing image at line {line_number}: "
                f"{image_path}"
            )
            missing_images += 1

        if "messages" not in sample:
            print(
                f"Missing messages at line {line_number}"
            )
            bad_samples += 1


print("\nValidation complete.")
print(f"Total samples:   {total}")
print(f"Missing images:  {missing_images}")
print(f"Bad samples:     {bad_samples}")