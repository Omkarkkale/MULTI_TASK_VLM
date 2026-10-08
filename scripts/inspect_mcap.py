from mcap.reader import make_reader

mcap_file = "/workspace/data/2026_08_22-14_26_18_eye_40.mcap"

with open(mcap_file, "rb") as f:
    reader = make_reader(f)
    summary = reader.get_summary()

    print("Topics found in MCAP:\n")

    for channel_id, channel in summary.channels.items():

        schema = summary.schemas.get(channel.schema_id)

        if schema:
            message_type = schema.name
        else:
            message_type = "Unknown"

        count = summary.statistics.channel_message_counts.get(
            channel_id, 0
        )

        print(f"Topic: {channel.topic}")
        print(f"Type:  {message_type}")
        print(f"Count: {count}")
        print("-" * 60)