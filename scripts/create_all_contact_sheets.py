from pathlib import Path
import csv
import math

from PIL import Image, ImageDraw, ImageFont


DATASET_ROOT = Path("/workspace/extracted/crusher_dataset_v2")

SAMPLES_PER_SHEET = 12

THUMB_WIDTH = 420
THUMB_HEIGHT = 260

LABEL_HEIGHT = 45

PAIR_WIDTH = THUMB_WIDTH * 2
PAIR_HEIGHT = THUMB_HEIGHT + LABEL_HEIGHT

COLUMNS = 2
ROWS = math.ceil(SAMPLES_PER_SHEET / COLUMNS)

SHEET_WIDTH = PAIR_WIDTH * COLUMNS
SHEET_HEIGHT = PAIR_HEIGHT * ROWS


def load_and_resize(path):
    image = Image.open(path).convert("RGB")
    image.thumbnail((THUMB_WIDTH, THUMB_HEIGHT))

    canvas = Image.new(
        "RGB",
        (THUMB_WIDTH, THUMB_HEIGHT),
        "black"
    )

    x = (THUMB_WIDTH - image.width) // 2
    y = (THUMB_HEIGHT - image.height) // 2

    canvas.paste(image, (x, y))

    return canvas


def create_contact_sheets(recording_dir):
    metadata_path = recording_dir / "metadata.csv"

    if not metadata_path.exists():
        print(f"Skipping {recording_dir.name}: no metadata.csv")
        return 0

    with open(metadata_path, newline="") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        print(f"Skipping {recording_dir.name}: no samples")
        return 0

    contact_dir = recording_dir / "contact_sheets"
    contact_dir.mkdir(parents=True, exist_ok=True)

    recording_id = recording_dir.name

    num_sheets = math.ceil(len(rows) / SAMPLES_PER_SHEET)

    for sheet_index in range(num_sheets):
        start = sheet_index * SAMPLES_PER_SHEET
        end = min(start + SAMPLES_PER_SHEET, len(rows))

        batch = rows[start:end]

        sheet = Image.new(
            "RGB",
            (SHEET_WIDTH, SHEET_HEIGHT),
            "white"
        )

        draw = ImageDraw.Draw(sheet)

        for local_index, row in enumerate(batch):
            grid_row = local_index // COLUMNS
            grid_col = local_index % COLUMNS

            x0 = grid_col * PAIR_WIDTH
            y0 = grid_row * PAIR_HEIGHT

            narrow_path = DATASET_ROOT / row["front_narrow"]
            wide_path = DATASET_ROOT / row["front_wide"]

            try:
                narrow_img = load_and_resize(narrow_path)
                wide_img = load_and_resize(wide_path)

            except Exception as e:
                print(
                    f"ERROR loading recording {recording_id} "
                    f"sample {row['sample']}: {e}"
                )
                continue

            sheet.paste(narrow_img, (x0, y0))
            sheet.paste(
                wide_img,
                (x0 + THUMB_WIDTH, y0)
            )

            fill_level = float(row["fill_level"])

            label = (
                f"Rec {recording_id} | "
                f"Sample {int(row['sample']):04d} | "
                f"Fill {fill_level:.0f}%"
            )

            draw.text(
                (x0 + 10, y0 + THUMB_HEIGHT + 10),
                label,
                fill="black"
            )

            draw.text(
                (x0 + 10, y0 + 10),
                "NARROW",
                fill="white"
            )

            draw.text(
                (x0 + THUMB_WIDTH + 10, y0 + 10),
                "WIDE",
                fill="white"
            )

        output_path = (
            contact_dir /
            f"contact_sheet_{sheet_index + 1:03d}.jpg"
        )

        sheet.save(
            output_path,
            quality=90
        )

    print(
        f"Recording {recording_id}: "
        f"{len(rows)} samples → {num_sheets} contact sheets"
    )

    return num_sheets


def main():
    recording_dirs = sorted(
        [
            p for p in DATASET_ROOT.iterdir()
            if p.is_dir() and p.name.isdigit()
        ],
        key=lambda p: int(p.name)
    )

    if not recording_dirs:
        print("No recording folders found.")
        return

    print(
        f"Found {len(recording_dirs)} recording folders.\n"
    )

    total_sheets = 0

    for recording_dir in recording_dirs:
        total_sheets += create_contact_sheets(recording_dir)

    print("\n" + "=" * 60)
    print("CONTACT SHEET GENERATION COMPLETE")
    print("=" * 60)
    print(f"Total contact sheets: {total_sheets}")


if __name__ == "__main__":
    main() 