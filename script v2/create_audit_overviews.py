"""Create compact wide-camera lighting overviews from existing audit previews."""
import json
from pathlib import Path
from PIL import Image, ImageDraw


def main():
    root = Path(__file__).resolve().parents[1] / "extracted/dataset_audit_v3"
    records = sorted(
        [json.loads(p.read_text()) for p in (root / "recordings").glob("*/audit.json")],
        key=lambda r: int(r["recording_id"]),
    )
    destination = root / "overviews"
    destination.mkdir(exist_ok=True)
    for start in range(0, len(records), 7):
        group = records[start:start + 7]
        canvas = Image.new("RGB", (1680, len(group) * 160), "white")
        draw = ImageDraw.Draw(canvas)
        for row, record in enumerate(group):
            y = row * 160
            draw.text((8, y + 5), f"eye {record['recording_id']} | {record['observed_fill_header_start_utc']} | candidates {record['synchronized_candidates']} | sampled wide view only", fill="black")
            with Image.open(root / record["preview_path"]) as sheet:
                for index in range(8):
                    top = 80 + index * 280
                    crop = sheet.crop((450, top, 870, top + 240)).resize((210, 120))
                    canvas.paste(crop, (index * 210, y + 30))
        target = destination / f"overview_{start // 7 + 1:02d}.jpg"
        canvas.save(target, quality=90)
        print(target)


if __name__ == "__main__":
    main()
