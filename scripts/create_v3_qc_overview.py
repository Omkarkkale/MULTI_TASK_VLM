from pathlib import Path
import pandas as pd
from PIL import Image, ImageDraw
import numpy as np

DATASET_ROOT = Path("/workspace/extracted/crusher_dataset_v3")
METADATA = DATASET_ROOT / "master_metadata_clean.csv"

OUTPUT = Path("/workspace/results/v3_qc_overview")
OUTPUT.mkdir(parents=True, exist_ok=True)

SAMPLES_PER_RECORDING = 12

THUMB_W = 360
THUMB_H = 220

PAIR_W = THUMB_W * 2
ROW_H = THUMB_H + 40


def load_img(path):
    img = Image.open(path).convert("RGB")
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


df = pd.read_csv(METADATA)

for recording_id, group in df.groupby("recording_id"):
    group = group.sort_values("sample").reset_index(drop=True)

    n = len(group)
    count = min(SAMPLES_PER_RECORDING, n)

    indices = np.linspace(
        0,
        n - 1,
        count,
        dtype=int
    )

    selected = group.iloc[indices]

    sheet = Image.new(
        "RGB",
        (PAIR_W, ROW_H * count),
        "white"
    )

    draw = ImageDraw.Draw(sheet)

    for row_idx, (_, row) in enumerate(selected.iterrows()):
        narrow_path = DATASET_ROOT / row["front_narrow"]
        wide_path = DATASET_ROOT / row["front_wide"]

        narrow = load_img(narrow_path)
        wide = load_img(wide_path)

        y = row_idx * ROW_H

        sheet.paste(narrow, (0, y))
        sheet.paste(wide, (THUMB_W, y))

        draw.text(
            (10, y + 10),
            "NARROW",
            fill="white"
        )

        draw.text(
            (THUMB_W + 10, y + 10),
            "WIDE",
            fill="white"
        )

        label = (
            f"REC {recording_id} | "
            f"Sample {int(row['sample']):04d} | "
            f"Fill {float(row['fill_level']):.0f}%"
        )

        draw.text(
            (10, y + THUMB_H + 10),
            label,
            fill="black"
        )

    out = OUTPUT / f"rec_{recording_id}_qc.jpg"

    sheet.save(out, quality=90)

    print(
        f"REC {recording_id}: "
        f"{n} clean samples -> "
        f"{count} reviewed samples"
    )

print()
print("QC overview saved to:")
print(OUTPUT)
