from pathlib import Path
import json


DATASET_DIR = Path(
    "/workspace/extracted/crusher_dataset_multicam"
)

INPUT_JSONL = DATASET_DIR / "smolvlm_multicam_dataset.jsonl"

OUTPUT_DIR = DATASET_DIR / "splits_cycle"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------
# 1. Load full dataset
# --------------------------------------------------

with open(INPUT_JSONL, "r") as f:
    samples = [json.loads(line) for line in f]

print(f"Total samples: {len(samples)}")


# --------------------------------------------------
# 2. Detect temporal cycles
#
# New cycle when fill level jumps upward
# by more than 10 percentage points.
# --------------------------------------------------

cycles = []
current_cycle = [samples[0]]

for previous, current in zip(samples[:-1], samples[1:]):

    previous_fill = float(
        previous["metadata"]["fill_level"]
    )

    current_fill = float(
        current["metadata"]["fill_level"]
    )

    jump = current_fill - previous_fill

    if jump > 10:
        cycles.append(current_cycle)
        current_cycle = [current]
    else:
        current_cycle.append(current)

cycles.append(current_cycle)


# --------------------------------------------------
# 3. Show detected cycles
# --------------------------------------------------

print()
print("Detected temporal cycles:")
print("-----------------------------------")

for i, cycle in enumerate(cycles):

    values = [
        float(sample["metadata"]["fill_level"])
        for sample in cycle
    ]

    first_sample = cycle[0]["metadata"]["sample"]
    last_sample = cycle[-1]["metadata"]["sample"]

    print(
        f"Cycle {i + 1}: "
        f"samples {first_sample}-{last_sample} | "
        f"N={len(cycle)} | "
        f"GT {min(values):.0f}-{max(values):.0f}%"
    )


# --------------------------------------------------
# 4. MANUAL PILOT SPLIT
#
# TRAIN:
#   Cycle 1
#   Cycle 4
#   Cycle 5
#   Cycle 8
#
# VALIDATION:
#   Cycle 3
#   Cycle 6
#
# TEST:
#   Cycle 2
#   Cycle 7
#
# IMPORTANT:
# cycle numbers below are zero-indexed in Python.
# --------------------------------------------------

train_cycle_ids = [0, 3, 4, 7]

validation_cycle_ids = [2, 5]

test_cycle_ids = [1, 6]


train_samples = [
    sample
    for cycle_id in train_cycle_ids
    for sample in cycles[cycle_id]
]

validation_samples = [
    sample
    for cycle_id in validation_cycle_ids
    for sample in cycles[cycle_id]
]

test_samples = [
    sample
    for cycle_id in test_cycle_ids
    for sample in cycles[cycle_id]
]


# --------------------------------------------------
# 5. Write JSONL files
# --------------------------------------------------

def write_jsonl(path, data):

    with open(path, "w") as f:

        for sample in data:
            f.write(json.dumps(sample) + "\n")


write_jsonl(
    OUTPUT_DIR / "train.jsonl",
    train_samples
)

write_jsonl(
    OUTPUT_DIR / "validation.jsonl",
    validation_samples
)

write_jsonl(
    OUTPUT_DIR / "test.jsonl",
    test_samples
)


# --------------------------------------------------
# 6. Distribution helper
# --------------------------------------------------

def describe(name, data):

    values = [
        float(sample["metadata"]["fill_level"])
        for sample in data
    ]

    sample_numbers = [
        sample["metadata"]["sample"]
        for sample in data
    ]

    print()
    print(name)
    print("-----------------------------------")

    print(f"Samples: {len(data)}")

    print(f"Min GT:  {min(values):.1f}%")
    print(f"Max GT:  {max(values):.1f}%")

    print(
        f"Mean GT: "
        f"{sum(values) / len(values):.2f}%"
    )

    print(
        f"Sample IDs: {sample_numbers}"
    )


# --------------------------------------------------
# 7. Show final split
# --------------------------------------------------

describe(
    "TRAIN",
    train_samples
)

describe(
    "VALIDATION",
    validation_samples
)

describe(
    "TEST",
    test_samples
)


# --------------------------------------------------
# 8. Sanity check
# --------------------------------------------------

total_split_samples = (
    len(train_samples)
    + len(validation_samples)
    + len(test_samples)
)

print()
print("-----------------------------------")
print(f"Total after split: {total_split_samples}")

if total_split_samples == len(samples):
    print("All samples assigned exactly once.")
else:
    print("WARNING: sample-count mismatch.")


print()
print("Final cycle-based split created:")
print(OUTPUT_DIR)