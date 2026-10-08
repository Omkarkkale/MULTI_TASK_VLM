from pathlib import Path
import math

import pandas as pd
from PIL import Image, ImageDraw


DATASET_ROOT = Path("/workspace/extracted/crusher_dataset_v3")
METADATA = DATASET_ROOT / "master_metadata_clean.csv"

OUTPUT_ROOT = Path("/workspace/results/v3_full_contact_sheets")

SAMPLES_PER_SHEET = 12

THUMB_W = 420
THUMB_H = 260
LABEL_H = 45

PAIR_W = THUMB_W * 2
PAIR_H = THUMB_H + LABEL_H

COLUMNS = 2
ROWS = math.ceil(SAMPLES_PER_SHEET / COLUMNS)

SHEET_W = PAIR_W * COLUMNS
SHEET_H = PAIR_H * ROWS


def load_image(path):
    image = Image.open(path).convert("RGB")
    image.thumbnail((THUMB_W, THUMB_H))

    canvas = Image.new(
        "RGB",
        (THUMB_W, THUMB_H),
        "black"
    )

    x = (THUMB_W - image.width) // 2
    y = (THUMB_H - image.height) // 2

    canvas.paste(image, (x, y))

    return canvas


def create_sheets(recording_id, group):

    rec_output = OUTPUT_ROOT / f"rec_{recording_id}"
    rec_output.mkdir(parents=True, exist_ok=True)

    group = group.sort_values("sample").reset_index(drop=True)

    num_sheets = math.ceil(
        len(group) / SAMPLES_PER_SHEET
    )

    for sheet_idx in range(num_sheets):

        start = sheet_idx * SAMPLES_PER_SHEET
        end = min(
            start + SAMPLES_PER_SHEET,
            len(group)
        )

        batch = group.iloc[start:end]

        sheet = Image.new(
            "RGB",
            (SHEET_W, SHEET_H),
            "white"
        )

        draw = ImageDraw.Draw(sheet)

        for local_idx, (_, row) in enumerate(batch.iterrows()):

            grid_row = local_idx // COLUMNS
            grid_col = local_idx % COLUMNS

            x0 = grid_col * PAIR_W
            y0 = grid_row * PAIR_H

            narrow_path = (
                DATASET_ROOT / row["front_narrow"]
            )

            wide_path = (
                DATASET_ROOT / row["front_wide"]
            )

            try:
                narrow = load_image(narrow_path)
                wide = load_image(wide_path)

            except Exception as e:
                print(
                    f"ERROR REC {recording_id} "
                    f"sample {row['sample']}: {e}"
                )
                continue

            sheet.paste(
                narrow,
                (x0, y0)
            )

            sheet.paste(
                wide,
                (x0 + THUMB_W, y0)
            )

            # Camera labels
            draw.text(
                (x0 + 10, y0 + 10),
                "NARROW",
                fill="white"
            )

            draw.text(
                (x0 + THUMB_W + 10, y0 + 10),
                "WIDE",
                fill="white"
            )

            # Sample label
            label = (
                f"REC {recording_id} | "
                f"Sample {int(row['sample']):04d} | "
                f"Fill {float(row['fill_level']):.0f}%"
            )

            draw.text(
                (
                    x0 + 10,
                    y0 + THUMB_H + 10
                ),
                label,
                fill="black"
            )

        output = (
            rec_output /
            f"sheet_{sheet_idx + 1:03d}.jpg"
        )

        sheet.save(
            output,
            quality=90
        )

    print(
        f"REC {recording_id}: "
        f"{len(group)} samples -> "
        f"{num_sheets} sheets"
    )

    return num_sheets


def main():

    OUTPUT_ROOT.mkdir(
        parents=True,
        exist_ok=True
    )

    df = pd.read_csv(METADATA)

    print("=" * 80)
    print("V3 FULL CONTACT SHEET GENERATION")
    print("=" * 80)

    print(
        f"Clean-manifest samples: {len(df)}"
    )

    print(
        f"Recordings: {df['recording_id'].nunique()}"
    )

    print()

    total_sheets = 0

    for recording_id, group in df.groupby(
        "recording_id",
        sort=True
    ):

        total_sheets += create_sheets(
            recording_id,
            group
        )

    print()
    print("=" * 80)
    print("COMPLETE")
    print("=" * 80)

    print(
        f"Samples represented : {len(df)}"
    )

    print(
        f"Total contact sheets: {total_sheets}"
    )

    print()
    print("Output:")
    print(OUTPUT_ROOT)


if __name__ == "__main__":
    main()
