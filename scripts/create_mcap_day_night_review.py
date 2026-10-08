from pathlib import Path
import re
import math

from PIL import Image, ImageDraw
from io import BytesIO

from mcap.reader import make_reader
from mcap_ros2.decoder import DecoderFactory


DATA_DIR = Path("/workspace/data")
OUTPUT_DIR = Path("/workspace/results/day_night_review")

CAMERA_TOPIC = "/sensor/camera/front_narrow/image_raw/compressed/throttled"

THUMB_W = 360
THUMB_H = 220

RECORDINGS_PER_SHEET = 6


def recording_id(path):
    m = re.search(r"_eye_(\d+)", path.stem)

    if not m:
        return "UNKNOWN"

    return m.group(1)


def count_frames(path):
    count = 0

    with open(path, "rb") as f:
        reader = make_reader(
            f,
            decoder_factories=[DecoderFactory()]
        )

        for schema, channel, message, ros_msg in reader.iter_decoded_messages():
            if channel.topic == CAMERA_TOPIC:
                count += 1

    return count


def extract_selected_frames(path, selected_indices):
    frames = {}

    with open(path, "rb") as f:
        reader = make_reader(
            f,
            decoder_factories=[DecoderFactory()]
        )

        camera_index = 0

        for schema, channel, message, ros_msg in reader.iter_decoded_messages():

            if channel.topic != CAMERA_TOPIC:
                continue

            if camera_index in selected_indices:
                try:
                    img = Image.open(
                        BytesIO(bytes(ros_msg.data))
                    ).convert("RGB")

                    frames[camera_index] = img.copy()

                except Exception as e:
                    print(
                        f"Could not decode {path.name} "
                        f"frame {camera_index}: {e}"
                    )

            camera_index += 1

    return frames


def resize_image(img):
    img = img.copy()
    img.thumbnail((THUMB_W, THUMB_H))

    canvas = Image.new(
        "RGB",
        (THUMB_W, THUMB_H),
        "black"
    )

    x = (THUMB_W - img.width) // 2
    y = (THUMB_H - img.height) // 2

    canvas.paste(img, (x, y))

    return canvas


def create_preview(path):
    rid = recording_id(path)

    total = count_frames(path)

    if total == 0:
        print(f"REC {rid}: no narrow frames")
        return None

    indices = sorted(
        set([
            0,
            total // 2,
            total - 1,
        ])
    )

    frames = extract_selected_frames(
        path,
        set(indices)
    )

    preview_w = THUMB_W * 3
    preview_h = THUMB_H + 55

    preview = Image.new(
        "RGB",
        (preview_w, preview_h),
        "white"
    )

    draw = ImageDraw.Draw(preview)

    labels = ["EARLY", "MIDDLE", "LATE"]

    for i, idx in enumerate(indices):
        if idx not in frames:
            continue

        img = resize_image(frames[idx])

        preview.paste(
            img,
            (i * THUMB_W, 0)
        )

        draw.text(
            (i * THUMB_W + 10, 10),
            labels[i],
            fill="white"
        )

    draw.text(
        (10, THUMB_H + 12),
        f"REC {rid} | frames={total} | {path.name}",
        fill="black"
    )

    out = OUTPUT_DIR / f"rec_{rid}_preview.jpg"

    preview.save(
        out,
        quality=90
    )

    print(
        f"REC {rid:>3}: "
        f"{total:>6} frames -> {out.name}"
    )

    return rid, preview


def create_contact_sheets(previews):

    sheet_w = THUMB_W * 3
    row_h = THUMB_H + 55

    number_of_sheets = math.ceil(
        len(previews) / RECORDINGS_PER_SHEET
    )

    for sheet_index in range(number_of_sheets):

        batch = previews[
            sheet_index * RECORDINGS_PER_SHEET:
            (sheet_index + 1) * RECORDINGS_PER_SHEET
        ]

        sheet = Image.new(
            "RGB",
            (
                sheet_w,
                row_h * len(batch)
            ),
            "white"
        )

        for row, (rid, preview) in enumerate(batch):

            sheet.paste(
                preview,
                (0, row * row_h)
            )

        out = (
            OUTPUT_DIR /
            f"review_sheet_{sheet_index + 1:02d}.jpg"
        )

        sheet.save(
            out,
            quality=90
        )


def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    mcaps = sorted(
        DATA_DIR.glob("*.mcap"),
        key=lambda p: int(recording_id(p))
    )

    print("=" * 80)
    print("MCAP DAY / NIGHT VISUAL REVIEW")
    print("=" * 80)
    print(f"MCAPs found: {len(mcaps)}")
    print()

    previews = []

    for i, path in enumerate(mcaps, start=1):

        print(
            f"[{i}/{len(mcaps)}] {path.name}"
        )

        result = create_preview(path)

        if result is not None:
            previews.append(result)

    create_contact_sheets(previews)

    print()
    print("=" * 80)
    print("REVIEW COMPLETE")
    print("=" * 80)
    print(f"Output: {OUTPUT_DIR}")
    print()
    print(
        "Open review_sheet_01.jpg, review_sheet_02.jpg, etc. "
        "in VS Code and classify each recording as DAY or NIGHT."
    )


if __name__ == "__main__":
    main()
