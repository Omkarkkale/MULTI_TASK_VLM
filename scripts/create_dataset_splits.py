from pathlib import Path
import json


DATASET_DIR = Path(
    "/workspace/extracted/crusher_dataset_multicam"
)

INPUT_JSONL = DATASET_DIR / "smolvlm_multicam_dataset.jsonl"

OUTPUT_DIR = DATASET_DIR / "splits"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


TRAIN_PATH = OUTPUT_DIR / "train.jsonl"
VAL_PATH = OUTPUT_DIR / "validation.jsonl"
TEST_PATH = OUTPUT_DIR / "test.jsonl"


# --------------------------------------------------
# 1. Load all samples
# --------------------------------------------------

with open(INPUT_JSONL, "r") as f:
    samples = [json.loads(line) for line in f]

print(f"Total samples loaded: {len(samples)}")


# --------------------------------------------------
# 2. Block-wise split
#
# Samples are already ordered in time.
#
# Train:      first 99
# Validation: next 12
# Test:       final 13
# --------------------------------------------------

train_samples = samples[:99]
val_samples = samples[99:111]
test_samples = samples[111:]


# --------------------------------------------------
# 3. Helper function to write JSONL
# --------------------------------------------------

def write_jsonl(path, data):

    with open(path, "w") as f:

        for sample in data:
            f.write(json.dumps(sample) + "\n")


# --------------------------------------------------
# 4. Save splits
# --------------------------------------------------

write_jsonl(TRAIN_PATH, train_samples)
write_jsonl(VAL_PATH, val_samples)
write_jsonl(TEST_PATH, test_samples)


# --------------------------------------------------
# 5. Print summary
# --------------------------------------------------

print()
print("Dataset split complete.")
print("-----------------------------------")
print(f"Train samples:      {len(train_samples)}")
print(f"Validation samples: {len(val_samples)}")
print(f"Test samples:       {len(test_samples)}")
print()
print(f"Train file:      {TRAIN_PATH}")
print(f"Validation file: {VAL_PATH}")
print(f"Test file:       {TEST_PATH}")


# --------------------------------------------------
# 6. Show sample-number ranges
# --------------------------------------------------

def sample_range(data):

    first = data[0]["metadata"]["sample"]
    last = data[-1]["metadata"]["sample"]

    return first, last


train_first, train_last = sample_range(train_samples)
val_first, val_last = sample_range(val_samples)
test_first, test_last = sample_range(test_samples)


print()
print("Sample ranges:")
print("-----------------------------------")
print(
    f"Train:      {train_first} -> {train_last}"
)
print(
    f"Validation: {val_first} -> {val_last}"
)
print(
    f"Test:       {test_first} -> {test_last}"
)