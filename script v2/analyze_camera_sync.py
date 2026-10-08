"""Measure selected camera-pair timestamp gaps and optionally activate a cutoff.

No rematching or image deletion. Original candidate metadata is preserved.
Without --max-pair-ms, this script only creates an analysis report.
"""
import argparse
from collections import defaultdict
import csv
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
import math
from pathlib import Path

from audit_mcap_dataset import PROJECT, write_csv
from camera_sync_policy import evaluate


def distribution(values):
    ordered = sorted(values)
    if not ordered:
        return {"count": 0}
    def percentile(q):
        index = (len(ordered) - 1) * q
        lo, hi = math.floor(index), math.ceil(index)
        return (ordered[lo] + (ordered[hi] - ordered[lo]) * (index - lo)) / 1_000_000
    return {"count": len(ordered), "exact_matches": sum(v == 0 for v in ordered), "min_ms": ordered[0] / 1_000_000, "median_ms": percentile(.5), "p90_ms": percentile(.9), "p95_ms": percentile(.95), "p99_ms": percentile(.99), "max_ms": ordered[-1] / 1_000_000}


def proposed_role(row):
    if row["suggested_lighting"] == "night_candidate":
        return "test_night"
    if row["suggested_lighting"] != "daylight_candidate":
        return "hold_lighting_review"
    date = datetime.fromtimestamp(int(row["fill_timestamp_ns"]) / 1e9, timezone.utc)
    year, week, _ = date.isocalendar()
    return {35: "train", 36: "validation", 37: "test_normal"}.get(week, "hold_date_review") if year == 2026 else "hold_date_review"


def retention(rows, limit_ns):
    groups = defaultdict(list)
    policy = {"max_image_gt_delta_ns": 1_000_000_000, "max_camera_pair_delta_ns": limit_ns}
    for row in rows:
        if evaluate(row, policy)["sync_status"] == "pass":
            groups[proposed_role(row)].append(float(row["fill_level"]))
    daylight = sum(len(groups[k]) for k in ("train", "validation", "test_normal"))
    roles = {}
    for key in ("train", "validation", "test_normal", "test_night", "hold_lighting_review", "hold_date_review"):
        values = groups[key]
        roles[key] = {"count": len(values), "min_fill": min(values) if values else None, "max_fill": max(values) if values else None, "daylight_split_percent": 100 * len(values) / daylight if daylight and key in ("train", "validation", "test_normal") else None, "fill_bins": [sum(lo <= v < hi for v in values) for lo, hi in [(0,10),(10,20),(20,30),(30,40),(40,50),(50,60),(60,70),(70,80),(80,90),(90,101)]]}
    count = sum(len(v) for v in groups.values())
    return {"max_pair_ms": limit_ns / 1_000_000, "retained": count, "rejected": len(rows) - count, "retained_percent": 100 * count / len(rows), "roles_before_visual_qc": roles}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=PROJECT / "extracted/crusher_dataset_v3_candidates")
    parser.add_argument("--max-pair-ms", help="Activate an inclusive camera-pair cutoff in milliseconds, e.g. 100 or 250")
    args = parser.parse_args()
    root = args.dataset.resolve()
    metadata = root / "metadata.csv"
    with metadata.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    if not rows or len({r["sample_id"] for r in rows}) != len(rows):
        parser.error("Expected nonempty metadata with unique sample IDs")
    selected_ns = None
    if args.max_pair_ms is not None:
        try:
            value = Decimal(args.max_pair_ms) * 1_000_000
            if not value.is_finite() or value < 0 or value != value.to_integral_value() or value > 2_000_000_000:
                raise ValueError("Use 0–2000 ms with integer-nanosecond precision")
            selected_ns = int(value)
        except (ValueError, InvalidOperation) as exc:
            parser.error(str(exc))
    baseline_policy = {"max_image_gt_delta_ns": 1_000_000_000, "max_camera_pair_delta_ns": 2_000_000_000}
    details, per_source = [], defaultdict(list)
    for row in rows:
        evaluated = evaluate(row, baseline_policy)
        if evaluated["sync_status"] != "pass":
            parser.error(f"Source candidate violates baseline sync rule: {row['sample_id']}")
        delta = evaluated["camera_pair_delta_ns"]
        details.append({"sample_id": row["sample_id"], "source_uid": row["source_uid"], "recording_id": row["recording_id"], "proposed_role": proposed_role(row), "fill_timestamp_ns": row["fill_timestamp_ns"], "narrow_timestamp_ns": row["narrow_timestamp_ns"], "wide_timestamp_ns": row["wide_timestamp_ns"], "camera_pair_delta_ns": delta, "camera_pair_delta_ms": delta / 1_000_000})
        per_source[row["source_uid"]].append(delta)
    report_dir = root / "camera_sync_analysis"
    report_dir.mkdir(exist_ok=True)
    write_csv(report_dir / "per_sample.csv", details, list(details[0]))
    record_stats = [{"source_uid": source, **distribution(values)} for source, values in sorted(per_source.items())]
    write_csv(report_dir / "per_recording.csv", record_stats, list(record_stats[0]))
    limits = sorted({0, 50_000_000, 100_000_000, 250_000_000, 500_000_000, 1_000_000_000, 2_000_000_000} | ({selected_ns} if selected_ns is not None else set()))
    report = {"scope": "Currently selected pairs only; alternative frames in raw MCAPs have not been searched for closer pairs", "metadata_sha256": hashlib.sha256(metadata.read_bytes()).hexdigest(), "observed": distribution([d["camera_pair_delta_ns"] for d in details]), "threshold_comparison": [retention(rows, limit) for limit in limits], "caveat": "ROS header stamp agreement does not establish exposure synchronization, shared clock accuracy or acceptable crusher motion. Limits are engineering policies, not validated task-specific accuracy thresholds."}
    if selected_ns is not None:
        policy = {"schema_version": 1, "max_image_gt_delta_ns": 1_000_000_000, "max_camera_pair_delta_ns": selected_ns, "inclusive": True, "pair_selection": "Existing independently nearest-to-GT pair; no rematching", "rationale": "User-selected tighter camera-pair bound after measured retention analysis; task-specific motion validation remains pending", "activated_at_utc": datetime.now(timezone.utc).isoformat(), "metadata_sha256_at_activation": report["metadata_sha256"]}
        accepted, rejected = [], []
        for row in rows:
            result = {**row, **evaluate(row, policy)}
            (accepted if result["sync_status"] == "pass" else rejected).append(result)
        fields = list(rows[0]) + [k for k in evaluate(rows[0], policy) if k not in rows[0]]
        write_csv(root / "sync_accepted.csv", accepted, fields)
        write_csv(root / "sync_rejected.csv", rejected, fields)
        temporary = root / "sync_policy.json.tmp"
        temporary.write_text(json.dumps(policy, indent=2))
        temporary.replace(root / "sync_policy.json")
        report["applied_policy"] = policy
        report["selected_result"] = retention(rows, selected_ns)
    (report_dir / "report.json").write_text(json.dumps(report, indent=2))
    observed = report["observed"]
    lines = ["# Camera-pair synchronization analysis", "", report["scope"], "", f"Pairs: {len(rows)}; exact matches: {observed['exact_matches']}.", "", f"Median: {observed['median_ms']:.3f} ms; p95: {observed['p95_ms']:.3f} ms; p99: {observed['p99_ms']:.3f} ms; maximum: {observed['max_ms']:.3f} ms.", "", "Both image-to-GT differences must remain <= 1,000 ms. All comparisons use integer nanoseconds.", "", "| Pair limit (ms) | Retained | % of original | Train | Validation | Test-normal | Night | Lighting hold |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for result in report["threshold_comparison"]:
        counts = result["roles_before_visual_qc"]
        lines.append(f"| {result['max_pair_ms']:g} | {result['retained']} | {result['retained_percent']:.2f}% | " + " | ".join(str(counts[k]["count"]) for k in ("train", "validation", "test_normal", "test_night", "hold_lighting_review")) + " |")
    if "selected_result" in report:
        result = report["selected_result"]
        lines += ["", f"## Applied camera-pair limit: {selected_ns / 1_000_000:g} ms", "", f"Retained: {result['retained']}; rejected by synchronization: {result['rejected']}. Full visual QC is still pending.", "", "| Daylight role | Candidates | % of retained daylight | Fill range |", "| --- | ---: | ---: | --- |"]
        for role in ("train", "validation", "test_normal"):
            stat = result["roles_before_visual_qc"][role]
            percentage = f"{stat['daylight_split_percent']:.2f}%" if stat['daylight_split_percent'] is not None else "N/A"
            lines.append(f"| {role} | {stat['count']} | {percentage} | {stat['min_fill']}–{stat['max_fill']}% |")
    lines += ["", report["caveat"], "", "Fill distributions and lighting/week roles are provisional. Night and transition-review candidates are excluded from daylight split percentages. No samples were rematched, approved for visual quality or frozen by this analysis."]
    (report_dir / "report.md").write_text("\n".join(lines) + "\n")
    print(json.dumps({"observed": report["observed"], "selected_result": report.get("selected_result"), "report": str(report_dir / "report.md")}, indent=2))


if __name__ == "__main__":
    main()
