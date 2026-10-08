from pathlib import Path
import csv

from mcap.reader import make_reader
from mcap_ros2.decoder import DecoderFactory


MCAP_PATH = Path(
    "/workspace/data/2026_08_22-14_26_18_eye_40.mcap"
)

NARROW_TOPIC = (
    "/sensor/camera/front_narrow/image_raw/compressed/throttled"
)

WIDE_TOPIC = (
    "/sensor/camera/front_wide/image_raw/compressed/throttled"
)

FILL_TOPIC = "/processing/crusher/fill_level"

OUTPUT_DIR = Path("/workspace/extracted/crusher_dataset_multicam")

NARROW_DIR = OUTPUT_DIR / "front_narrow"
WIDE_DIR = OUTPUT_DIR / "front_wide"

METADATA_PATH = OUTPUT_DIR / "metadata.csv"

# Confirmed with Bjarne
MAX_DELTA_SECONDS = 1.0


def header_stamp_to_ns(ros_msg):
    return (
        ros_msg.header.stamp.sec * 1_000_000_000
        + ros_msg.header.stamp.nanosec
    )


def find_nearest(messages, target_timestamp):
    return min(
        range(len(messages)),
        key=lambda i: abs(
            messages[i]["timestamp"] - target_timestamp
        ),
    )


NARROW_DIR.mkdir(parents=True, exist_ok=True)
WIDE_DIR.mkdir(parents=True, exist_ok=True)


narrow_messages = []
wide_messages = []
fill_messages = []


print("Reading MCAP...")


with open(MCAP_PATH, "rb") as f:
    reader = make_reader(
        f,
        decoder_factories=[DecoderFactory()],
    )

    for schema, channel, message, ros_msg in reader.iter_decoded_messages(
        topics=[
            NARROW_TOPIC,
            WIDE_TOPIC,
            FILL_TOPIC,
        ]
    ):

        if channel.topic == NARROW_TOPIC:

            narrow_messages.append(
                {
                    "timestamp": header_stamp_to_ns(ros_msg),
                    "data": bytes(ros_msg.data),
                }
            )

        elif channel.topic == WIDE_TOPIC:

            wide_messages.append(
                {
                    "timestamp": header_stamp_to_ns(ros_msg),
                    "data": bytes(ros_msg.data),
                }
            )

        elif channel.topic == FILL_TOPIC:

            fill_messages.append(
                {
                    "timestamp": header_stamp_to_ns(ros_msg),
                    "fill_level": float(ros_msg.data),
                }
            )


print()
print(f"Front narrow messages: {len(narrow_messages)}")
print(f"Front wide messages:   {len(wide_messages)}")
print(f"Fill-level messages:   {len(fill_messages)}")
print()


rows = []

kept = 0
rejected = 0


for fill_index, fill in enumerate(fill_messages):

    fill_timestamp = fill["timestamp"]

    narrow_index = find_nearest(
        narrow_messages,
        fill_timestamp,
    )

    wide_index = find_nearest(
        wide_messages,
        fill_timestamp,
    )

    narrow = narrow_messages[narrow_index]
    wide = wide_messages[wide_index]

    narrow_signed_delta = (
        narrow["timestamp"] - fill_timestamp
    ) / 1e9

    wide_signed_delta = (
        wide["timestamp"] - fill_timestamp
    ) / 1e9

    narrow_delta = abs(narrow_signed_delta)
    wide_delta = abs(wide_signed_delta)

    # Both camera views must satisfy the 1-second rule.
    if (
        narrow_delta > MAX_DELTA_SECONDS
        or wide_delta > MAX_DELTA_SECONDS
    ):
        rejected += 1

        print(
            f"REJECT fill {fill_index + 1:03d} | "
            f"value={fill['fill_level']:.1f}% | "
            f"narrow Δt={narrow_delta:.3f}s | "
            f"wide Δt={wide_delta:.3f}s"
        )

        continue

    kept += 1

    sample_name = f"sample_{kept:03d}"

    narrow_filename = f"{sample_name}_narrow.jpg"
    wide_filename = f"{sample_name}_wide.jpg"

    narrow_path = NARROW_DIR / narrow_filename
    wide_path = WIDE_DIR / wide_filename

    narrow_path.write_bytes(narrow["data"])
    wide_path.write_bytes(wide["data"])

    rows.append(
        {
            "sample": kept,
            "front_narrow": f"front_narrow/{narrow_filename}",
            "front_wide": f"front_wide/{wide_filename}",
            "fill_level": fill["fill_level"],

            "fill_timestamp_ns": fill_timestamp,

            "narrow_camera_index": narrow_index,
            "narrow_timestamp_ns": narrow["timestamp"],
            "narrow_delta_t_seconds": round(
                narrow_delta, 6
            ),
            "narrow_signed_delta_t_seconds": round(
                narrow_signed_delta, 6
            ),

            "wide_camera_index": wide_index,
            "wide_timestamp_ns": wide["timestamp"],
            "wide_delta_t_seconds": round(
                wide_delta, 6
            ),
            "wide_signed_delta_t_seconds": round(
                wide_signed_delta, 6
            ),
        }
    )

    print(
        f"KEEP   {sample_name} | "
        f"fill={fill['fill_level']:.1f}% | "
        f"narrow Δt={narrow_delta:.3f}s | "
        f"wide Δt={wide_delta:.3f}s"
    )


fieldnames = [
    "sample",
    "front_narrow",
    "front_wide",
    "fill_level",
    "fill_timestamp_ns",

    "narrow_camera_index",
    "narrow_timestamp_ns",
    "narrow_delta_t_seconds",
    "narrow_signed_delta_t_seconds",

    "wide_camera_index",
    "wide_timestamp_ns",
    "wide_delta_t_seconds",
    "wide_signed_delta_t_seconds",
]


with open(METADATA_PATH, "w", newline="") as csvfile:

    writer = csv.DictWriter(
        csvfile,
        fieldnames=fieldnames,
    )

    writer.writeheader()
    writer.writerows(rows)


print()
print("Export complete.")
print(f"Kept samples:     {kept}")
print(f"Rejected samples: {rejected}")
print(f"Metadata:         {METADATA_PATH}")
print(f"Narrow images:    {NARROW_DIR}")
print(f"Wide images:      {WIDE_DIR}")