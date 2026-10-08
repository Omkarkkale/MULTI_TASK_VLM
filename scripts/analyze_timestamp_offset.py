from mcap.reader import make_reader
from mcap_ros2.decoder import DecoderFactory

mcap_file = "/workspace/data/2026_08_22-14_26_18_eye_40.mcap"

topics = [
    "/sensor/camera/front_narrow/image_raw/compressed/throttled",
    "/processing/crusher/fill_level",
]

results = {topic: [] for topic in topics}

with open(mcap_file, "rb") as f:
    reader = make_reader(
        f,
        decoder_factories=[DecoderFactory()]
    )

    for schema, channel, message, ros_msg in reader.iter_decoded_messages(
        topics=topics
    ):

        header_ns = (
            ros_msg.header.stamp.sec * 1_000_000_000
            + ros_msg.header.stamp.nanosec
        )

        offset_seconds = (
            message.log_time - header_ns
        ) / 1e9

        results[channel.topic].append(offset_seconds)


for topic, offsets in results.items():

    print("\n" + "=" * 70)
    print(topic)
    print("=" * 70)

    print("Messages:", len(offsets))
    print(f"Minimum offset: {min(offsets):.3f} s")
    print(f"Maximum offset: {max(offsets):.3f} s")
    print(f"Average offset: {sum(offsets)/len(offsets):.3f} s")

    print("\nFirst 10 offsets:")

    for offset in offsets[:10]:
        print(f"{offset:.3f} s")