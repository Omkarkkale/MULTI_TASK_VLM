from mcap.reader import make_reader
from mcap_ros2.decoder import DecoderFactory

mcap_file = "/workspace/data/2026_08_22-14_26_18_eye_40.mcap"

camera_topic = "/sensor/camera/front_narrow/image_raw/compressed/throttled"
fill_topic = "/processing/crusher/fill_level"


# Convert ROS header.stamp into nanoseconds
def header_stamp_to_ns(ros_msg):
    return (
        ros_msg.header.stamp.sec * 1_000_000_000
        + ros_msg.header.stamp.nanosec
    )


camera_messages = []
fill_messages = []


# --------------------------------------------------
# Read camera messages
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
            "timestamp": header_stamp_to_ns(ros_msg),
            "data": ros_msg.data,
            "format": ros_msg.format
        })


# --------------------------------------------------
# Read fill-level messages
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
            "timestamp": header_stamp_to_ns(ros_msg),
            "value": ros_msg.data
        })


print(f"Camera messages: {len(camera_messages)}")
print(f"Fill messages:   {len(fill_messages)}")

print(
    "\nNearest camera frame for each fill measurement "
    "using header.stamp:\n"
)


# --------------------------------------------------
# Synchronize fill measurements with camera frames
# --------------------------------------------------

for fill_index, fill in enumerate(fill_messages):

    # Find camera frame with smallest timestamp difference
    nearest_camera_index = min(
        range(len(camera_messages)),
        key=lambda i: abs(
            camera_messages[i]["timestamp"]
            - fill["timestamp"]
        )
    )

    camera = camera_messages[nearest_camera_index]

    # Signed difference:
    # positive = camera happened AFTER fill measurement
    # negative = camera happened BEFORE fill measurement
    signed_difference_ns = (
        camera["timestamp"]
        - fill["timestamp"]
    )

    signed_difference_seconds = (
        signed_difference_ns / 1e9
    )

    # Absolute difference = synchronization distance
    time_difference_seconds = abs(
        signed_difference_seconds
    )

    print(
        f"Fill {fill_index + 1:03d} | "
        f"Camera {nearest_camera_index + 1:04d} | "
        f"Value: {fill['value']:.1f} | "
        f"Δt: {time_difference_seconds:.3f} s | "
        f"signed: {signed_difference_seconds:+.3f} s"
    )