from pathlib import Path
import csv
from PIL import Image, ImageOps, ImageDraw

DATASET_DIR = Path("/workspace/extracted/crusher_dataset_multicam")
METADATA_PATH = DATASET_DIR / "metadata.csv"
OUTPUT_DIR = DATASET_DIR / "contact_sheets"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

IMAGE_WIDTH = 420
IMAGE_HEIGHT = 260
TEXT_HEIGHT = 50

SAMPLES_PER_SHEET = 12
COLUMNS = 2


def fit_image(path):
    img = Image.open(path).convert("RGB")
    return ImageOps.fit(
        img,
        (IMAGE_WIDTH, IMAGE_HEIGHT),
        method=Image.Resampling.LANCZOS,
    )


with open(METADATA_PATH, newline="") as f:
    rows = list(csv.DictReader(f))


for sheet_start in range(0, len(rows), SAMPLES_PER_SHEET):

    sheet_rows = rows[
        sheet_start : sheet_start + SAMPLES_PER_SHEET
    ]

    rows_per_sheet = len(sheet_rows)

    canvas_width = IMAGE_WIDTH * 2

    sample_block_height = (
        TEXT_HEIGHT + IMAGE_HEIGHT
    )

    canvas_height = (
        sample_block_height * rows_per_sheet
    )

    canvas = Image.new(
        "RGB",
        (canvas_width, canvas_height),
        "white",
    )

    draw = ImageDraw.Draw(canvas)

    for i, row in enumerate(sheet_rows):

        y = i * sample_block_height

        sample = row["sample"]
        fill_level = row["fill_level"]

        narrow_path = DATASET_DIR / row["front_narrow"]
        wide_path = DATASET_DIR / row["front_wide"]

        narrow = fit_image(narrow_path)
        wide = fit_image(wide_path)

        label = (
            f"Sample {sample} | "
            f"Fill level: {fill_level}%"
        )

        draw.text(
            (10, y + 10),
            label,
            fill="black",
        )

        canvas.paste(
            narrow,
            (0, y + TEXT_HEIGHT),
        )

        canvas.paste(
            wide,
            (IMAGE_WIDTH, y + TEXT_HEIGHT),
        )

        draw.text(
            (10, y + TEXT_HEIGHT + 5),
            "NARROW",
            fill="white",
        )

        draw.text(
            (
                IMAGE_WIDTH + 10,
                y + TEXT_HEIGHT + 5,
            ),
            "WIDE",
            fill="white",
        )

    sheet_number = (
        sheet_start // SAMPLES_PER_SHEET
    ) + 1

    output_path = (
        OUTPUT_DIR
        / f"contact_sheet_{sheet_number:02d}.jpg"
    )

    canvas.save(
        output_path,
        quality=90,
    )

    print(f"Saved: {output_path}")


print()
print("Done.")
print(f"Total samples: {len(rows)}")
print(f"Contact sheets: {OUTPUT_DIR}")