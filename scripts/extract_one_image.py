from mcap.reader import make_reader
from mcap_ros2.decoder import DecoderFactory

mcap_file = "/workspace/data/2026_08_22-13_10_54_eye_0.mcap"

camera_topic = "/sensor/camera/front/image_raw/compressed/throttled"

output_file = "/workspace/extracted/images/frame_0001.jpg"

with open(mcap_file, "rb") as f:
    reader = make_reader(
        f,
        decoder_factories=[DecoderFactory()]
    )

    for schema, channel, message, ros_msg in reader.iter_decoded_messages(
        topics=[camera_topic]
    ):
        print("Found camera message")
        print("Timestamp:", message.log_time)
        print("Format:", ros_msg.format)

        with open(output_file, "wb") as img:
            img.write(ros_msg.data)

        print("Saved:", output_file)

        break