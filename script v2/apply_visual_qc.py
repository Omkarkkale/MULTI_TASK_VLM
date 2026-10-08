"""Apply manual decisions to candidate metadata without deleting source images.

Only explicitly kept, successfully decoded pairs enter the visual-keep manifest.
Lighting-pending pairs are withheld from the daylight/night candidate manifests.
Outputs remain unsplit and require session/leakage review before dataset freeze.
"""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from audit_mcap_dataset import PROJECT, write_csv
from camera_sync_policy import evaluate, load_policy


def read_csv(path):
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=PROJECT / "extracted/crusher_dataset_v3_candidates")
    parser.add_argument("--decisions", type=Path, required=True)
    parser.add_argument("--output", type=Path, help="New directory; defaults to a timestamped folder under dataset/qc_results")
    args = parser.parse_args()
    root = args.dataset.resolve()
    try:
        sync_policy = load_policy(root)
    except ValueError as exc:
        parser.error(str(exc))
    rows = read_csv(root / "metadata.csv")
    source_ids = {r["sample_id"] for r in rows}
    if not rows or len(source_ids) != len(rows):
        parser.error("Candidate metadata is empty or contains duplicate sample IDs")
    decisions = {}
    for decision in read_csv(args.decisions):
        sid = decision.get("sample_id", "")
        if sid not in source_ids or sid in decisions:
            parser.error(f"Unknown or duplicate decision sample ID: {sid}")
        if decision.get("qc") not in ("pending", "keep", "reject"):
            parser.error(f"Invalid QC decision: {sid}")
        if decision.get("lighting") not in ("pending", "daylight", "night", "transition", "uncertain"):
            parser.error(f"Invalid lighting decision: {sid}")
        if decision["qc"] == "reject" and not decision.get("reason", "").strip():
            parser.error(f"Rejection requires a reason: {sid}")
        decisions[sid] = decision
    groups = {name: [] for name in ("visual_keep", "rejected", "sync_rejected", "pending_qc", "daylight_candidates", "night_candidates", "lighting_hold")}
    for original in rows:
        row = dict(original)
        decision = decisions.get(row["sample_id"], {"qc": "pending", "lighting": "pending"})
        row.update(visual_qc=decision["qc"], lighting=decision["lighting"], qc_reason=decision.get("reason", ""), obstructed_view=decision.get("obstructed_view", ""), reviewed_at=decision.get("reviewed_at", ""), split="unassigned")
        row.update(evaluate(row, sync_policy))
        if row["sync_status"] != "pass":
            groups["sync_rejected"].append(row)
        elif row["visual_qc"] == "reject":
            groups["rejected"].append(row)
        elif row["visual_qc"] == "pending":
            groups["pending_qc"].append(row)
        else:
            if row["export_status"] != "decoded_candidate":
                parser.error(f"Cannot keep a pair with decode failure: {row['sample_id']}")
            for view in ("narrow", "wide"):
                image_path = (root / row[f"{view}_image"]).resolve()
                if not image_path.is_relative_to(root) or not image_path.is_file():
                    parser.error(f"Missing or invalid {view} image for {row['sample_id']}")
            groups["visual_keep"].append(row)
            if row["lighting"] == "daylight":
                groups["daylight_candidates"].append(row)
            elif row["lighting"] == "night":
                groups["night_candidates"].append(row)
            else:
                groups["lighting_hold"].append(row)
    output = args.output or root / "qc_results" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    if output.exists():
        parser.error("Output already exists; choose a new directory to preserve earlier review results")
    output.mkdir(parents=True)
    fields = list(rows[0]) + [name for name in ("qc_reason", "obstructed_view", "reviewed_at", "camera_pair_delta_ns", "camera_pair_delta_ms", "sync_status", "sync_reason") if name not in rows[0]]
    for name, selected in groups.items():
        write_csv(output / f"{name}.csv", selected, fields)
    (output / "decisions_applied.csv").write_bytes(args.decisions.read_bytes())
    summary = {
        "source_candidates": len(rows),
        "counts": {name: len(selected) for name, selected in groups.items()},
        "count_note": "visual_keep equals daylight_candidates + night_candidates + lighting_hold; these are overlapping summary categories",
        "metadata_sha256": hashlib.sha256((root / "metadata.csv").read_bytes()).hexdigest(),
        "decisions_sha256": hashlib.sha256(args.decisions.read_bytes()).hexdigest(),
        "status": "manual_qc_applied_not_frozen",
        "sync_policy": sync_policy,
        "remaining": "Finish pending reviews, confirm recording/session separation, recompute splits and distributions, then freeze.",
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    print(f"Saved QC manifests to {output}")


if __name__ == "__main__":
    main()
