"""Shared integer-nanosecond checks for GT and camera-pair synchronization."""
import json
from pathlib import Path


def evaluate(row, policy):
    try:
        gt, narrow, wide = (int(row[k]) for k in ("fill_timestamp_ns", "narrow_timestamp_ns", "wide_timestamp_ns"))
        if min(gt, narrow, wide) <= 0:
            raise ValueError("Nonpositive timestamp")
    except (ValueError, KeyError, TypeError):
        return {"camera_pair_delta_ns": "", "camera_pair_delta_ms": "", "sync_status": "reject", "sync_reason": "invalid_timestamp"}
    delta = abs(narrow - wide)
    reasons = []
    if abs(narrow - gt) > policy["max_image_gt_delta_ns"]:
        reasons.append("narrow_gt_delta_exceeded")
    if abs(wide - gt) > policy["max_image_gt_delta_ns"]:
        reasons.append("wide_gt_delta_exceeded")
    if delta > policy["max_camera_pair_delta_ns"]:
        reasons.append("camera_pair_delta_exceeded")
    return {"camera_pair_delta_ns": delta, "camera_pair_delta_ms": delta / 1_000_000, "sync_status": "reject" if reasons else "pass", "sync_reason": ";".join(reasons)}


def load_policy(dataset):
    path = Path(dataset) / "sync_policy.json"
    if not path.is_file():
        raise ValueError("No active sync policy. Run analyze_camera_sync.py with --max-pair-ms first.")
    policy = json.loads(path.read_text())
    for field in ("max_image_gt_delta_ns", "max_camera_pair_delta_ns"):
        if type(policy.get(field)) is not int or policy[field] < 0:
            raise ValueError(f"Invalid sync policy field: {field}")
    if policy["max_image_gt_delta_ns"] != 1_000_000_000:
        raise ValueError("This pipeline requires the existing 1-second image-to-GT limit")
    return policy
