"""Generate a local, one-pair-at-a-time manual obstruction review page.

Run with the Mac's Python; no third-party dependencies are required.
Images and source metadata are never modified by this script.
"""
import argparse
import csv
import json
from pathlib import Path
from camera_sync_policy import evaluate, load_policy

PROJECT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=PROJECT / "extracted/crusher_dataset_v3_candidates")
    args = parser.parse_args()
    root = args.dataset.resolve()
    with (root / "metadata.csv").open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    if not rows or len({r["sample_id"] for r in rows}) != len(rows):
        parser.error("Metadata must contain nonempty, unique sample IDs")
    fields = ["sample_id", "recording_id", "fill_level", "fill_timestamp_ns", "suggested_lighting", "export_status", "narrow_image", "wide_image", "narrow_signed_delta_seconds", "wide_signed_delta_seconds"]
    policy = load_policy(root) if (root / "sync_policy.json").exists() else None
    for row in rows:
        row.update(evaluate(row, policy) if policy else {"camera_pair_delta_ms": abs(int(row["narrow_timestamp_ns"]) - int(row["wide_timestamp_ns"])) / 1_000_000, "sync_status": "not_enforced", "sync_reason": "No active camera-pair policy"})
        row["max_camera_pair_ms"] = policy["max_camera_pair_delta_ns"] / 1_000_000 if policy else None
    fields += ["camera_pair_delta_ms", "sync_status", "sync_reason", "max_camera_pair_ms"]
    rows.sort(key=lambda r: (int(r["fill_timestamp_ns"]), r["sample_id"]))
    payload = json.dumps([{k: r[k] for k in fields} for r in rows]).replace("<", "\\u003c")
    template = Path(__file__).with_name("obstruction_review_template.html").read_text()
    target = root / "obstruction_review.html"
    target.write_text(template.replace("__SAMPLE_DATA__", payload))
    print(f"Created {target} with {len(rows)} sample pairs")


if __name__ == "__main__":
    main()
