from mcap.reader import make_reader
from mcap_ros2.decoder import DecoderFactory

mcap_file = "/workspace/data/2026_08_22-14_26_18_eye_40.mcap"

camera_topic = "/sensor/camera/front_narrow/image_raw/compressed/throttled"
fill_topic = "/processing/crusher/fill_level"

camera_messages = []
fill_messages = []


# --------------------------------------------------
# 1. Read camera timestamps
# --------------------------------------------------

with open(mcap_file, "rb") as f:
    reader = make_reader(
        f,
        decoder_factories=[DecoderFactory()]
    )

    for schema, channel, message, ros_msg in reader.iter_decoded_messages(
        topics=[camera_topic]
    ):
        camera_messages.append({
            "timestamp": message.log_time,
            "data": ros_msg.data,
            "format": ros_msg.format
        })


# --------------------------------------------------
# 2. Read fill-level timestamps + values
# --------------------------------------------------

with open(mcap_file, "rb") as f:
    reader = make_reader(
        f,
        decoder_factories=[DecoderFactory()]
    )

    for schema, channel, message, ros_msg in reader.iter_decoded_messages(
        topics=[fill_topic]
    ):
        fill_messages.append({
            "timestamp": message.log_time,
            "value": ros_msg.data
        })


print(f"Camera messages: {len(camera_messages)}")
print(f"Fill messages:   {len(fill_messages)}")

print("\nNearest camera frame for each fill measurement:\n")


# --------------------------------------------------
# 3. Find nearest camera for every fill measurement
# --------------------------------------------------

for fill_index, fill in enumerate(fill_messages):

    nearest_camera_index = min(
        range(len(camera_messages)),
        key=lambda i: abs(
            camera_messages[i]["timestamp"] - fill["timestamp"]
        )
    )

    camera = camera_messages[nearest_camera_index]

    time_difference_ns = abs(
        camera["timestamp"] - fill["timestamp"]
    )

    time_difference_seconds = time_difference_ns / 1e9

    print(
        f"Fill {fill_index + 1:02d} | "
        f"Camera {nearest_camera_index + 1:03d} | "
        f"Value: {fill['value']:.1f} | "
        f"Δt: {time_difference_seconds:.3f} s"
    )