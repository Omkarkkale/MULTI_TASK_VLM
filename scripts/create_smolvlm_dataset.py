import csv
import json
import os


# --------------------------------------------------
# Configuration
# --------------------------------------------------

dataset_dir = "/workspace/extracted/crusher_dataset"

csv_file = os.path.join(
    dataset_dir,
    "metadata.csv"
)

output_file = os.path.join(
    dataset_dir,
    "smolvlm_dataset.jsonl"
)

image_folder_name = "images"

prompt = "What is the crusher fill level?"


# --------------------------------------------------
# Read metadata and create VLM samples
# --------------------------------------------------

samples = []

with open(csv_file, "r") as f:

    reader = csv.DictReader(f)

    for row in reader:

        image_name = row["image"]

        fill_level = float(
            row["fill_level"]
        )

        # Convert 25.0 -> "25%"
        # If we later need decimals, we can change this.
        answer = f"{fill_level:.0f}%"

        sample = {

            "image": os.path.join(
                image_folder_name,
                image_name
            ),

            "messages": [

                {
                    "role": "user",
                    "content": [

                        {
                            "type": "image"
                        },

                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                },

                {
                    "role": "assistant",
                    "content": [

                        {
                            "type": "text",
                            "text": answer
                        }
                    ]
                }
            ],

            # Keep useful metadata.
            # These fields are not model inputs.
            "metadata": {
                "fill_level": fill_level,
                "camera_index": int(
                    row["camera_index"]
                ),
                "delta_t_seconds": float(
                    row["delta_t_seconds"]
                ),
                "signed_delta_t_seconds": float(
                    row["signed_delta_t_seconds"]
                )
            }
        }

        samples.append(sample)


# --------------------------------------------------
# Save JSONL
# --------------------------------------------------

with open(output_file, "w") as f:

    for sample in samples:

        json.dump(sample, f)
        f.write("\n")


# --------------------------------------------------
# Summary
# --------------------------------------------------

print("\nSmolVLM dataset created successfully.\n")

print(f"Samples: {len(samples)}")
print(f"Output:  {output_file}")

print("\nExample sample:\n")

print(
    json.dumps(
        samples[0],
        indent=2
    )
)