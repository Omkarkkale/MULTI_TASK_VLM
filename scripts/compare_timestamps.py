from mcap.reader import make_reader
from mcap_ros2.decoder import DecoderFactory

mcap_file = "/workspace/data/2026_08_22-14_26_18_eye_40.mcap"

topics = [
    "/sensor/camera/front_narrow/image_raw/compressed/throttled",
    "/processing/crusher/fill_level",
]

with open(mcap_file, "rb") as f:
    reader = make_reader(
        f,
        decoder_factories=[DecoderFactory()]
    )

    seen = set()

    for schema, channel, message, ros_msg in reader.iter_decoded_messages(
        topics=topics
    ):
        if channel.topic in seen:
            continue

        print("\nTOPIC:")
        print(channel.topic)

        print("MCAP log time:")
        print(message.log_time)

        header_ns = (
            ros_msg.header.stamp.sec * 1_000_000_000
            + ros_msg.header.stamp.nanosec
        )

        print("ROS header time:")
        print(header_ns)

        difference = abs(message.log_time - header_ns) / 1e9

        print("log_time - header.stamp:")
        print(f"{difference:.6f} seconds")

        seen.add(channel.topic)

        if len(seen) == len(topics):
            break