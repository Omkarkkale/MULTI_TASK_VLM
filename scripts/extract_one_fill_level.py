from mcap.reader import make_reader
from mcap_ros2.decoder import DecoderFactory

mcap_file = "/workspace/data/2026_08_22-13_10_54_eye_0.mcap"

fill_topic = "/processing/crusher/fill_level"

with open(mcap_file, "rb") as f:
    reader = make_reader(
        f,
        decoder_factories=[DecoderFactory()]
    )

    for schema, channel, message, ros_msg in reader.iter_decoded_messages(
        topics=[fill_topic]
    ):
        print("Found fill-level message")
        print("Timestamp:", message.log_time)
        print("Fill level:", ros_msg.data)

        break