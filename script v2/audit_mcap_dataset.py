"""Inventory all MCAPs, check label/image synchronization, and create review previews.

Writes only to a new audit directory. No lighting or week assignments are inferred
from filenames; filename hints and observed ROS times are recorded separately.
Run inside the project container: python3 "script v2/audit_mcap_dataset.py"
"""
import argparse
from bisect import bisect_left
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
from io import BytesIO
import json
import math
from pathlib import Path
import random
import re

PROJECT = Path(__file__).resolve().parents[1]
TOPICS = {
    "fill": "/processing/crusher/fill_level",
    "narrow": "/sensor/camera/front_narrow/image_raw/compressed/throttled",
    "wide": "/sensor/camera/front_wide/image_raw/compressed/throttled",
}
SCHEMA_VERSION = 1


def write_csv(path, rows, fields):
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


def source_identity(path, data_dir):
    relative = path.relative_to(data_dir).as_posix()
    match = re.search(r"_eye_(\d+)(?:_|$)", path.stem)
    recording_id = match.group(1) if match else "unknown"
    # Path identity, NOT a content checksum. Size/mtime are used for resume checks.
    uid = f"eye_{recording_id}_{hashlib.sha256(relative.encode()).hexdigest()[:12]}"
    return relative, recording_id, uid


def utc(ns):
    if ns is None:
        return ""
    return datetime.fromtimestamp(ns / 1e9, timezone.utc).isoformat()


def stamp_ns(msg):
    stamp = msg.header.stamp
    sec, nano = int(stamp.sec), int(stamp.nanosec)
    if sec < 0 or not 0 <= nano < 1_000_000_000 or sec * 1_000_000_000 + nano <= 0:
        raise ValueError("Invalid or zero header stamp")
    return sec * 1_000_000_000 + nano


def nearest(target, ordered, timestamps):
    if not ordered:
        return None
    position = bisect_left(timestamps, target)
    candidates = ordered[max(0, position - 1):min(len(ordered), position + 1)]
    return min(candidates, key=lambda x: (abs(x["timestamp_ns"] - target), x["timestamp_ns"], x["index"]))


def preview_indices(count, number):
    if not count:
        return set()
    if number == 1:
        return {count // 2}
    return {round(i * (count - 1) / (number - 1)) for i in range(number)}


def thumb(data):
    from PIL import Image, ImageOps
    with Image.open(BytesIO(data)) as im:
        im.load()
        return ImageOps.contain(im.convert("RGB"), (420, 240)).copy()


def contact_sheet(path, source, previews, number):
    from PIL import Image, ImageDraw
    sheet = Image.new("RGB", (880, 55 + number * 280), "#eeeeee")
    draw = ImageDraw.Draw(sheet)
    draw.text((12, 8), source, fill="black")
    draw.text((12, 26), "Temporal previews only; not full QC. Narrow (left), wide (right). Times are observed ROS header UTC.", fill="black")
    for column, view in enumerate(("narrow", "wide")):
        ordered = sorted(previews[view], key=lambda x: x["index"])
        for row, preview in enumerate(ordered):
            x, y = 10 + 440 * column, 55 + 280 * row
            draw.text((x, y), f"{view} frame {preview['index']} | {utc(preview['timestamp_ns'])}", fill="black")
            if preview["image"] is not None:
                sheet.paste(preview["image"], (x, y + 25))
            else:
                draw.text((x, y + 45), f"DECODE ERROR: {preview['error'][:70]}", fill="red")
    sheet.save(path, quality=85)


def scan(path, data_dir, output, number):
    from mcap.reader import make_reader
    from mcap_ros2.decoder import DecoderFactory
    relative, recording_id, uid = source_identity(path, data_dir)
    stat = path.stat()
    record_dir = output / "recordings" / uid
    record_dir.mkdir(parents=True, exist_ok=True)
    checkpoint = record_dir / "audit.json"
    if checkpoint.exists():
        cached = json.loads(checkpoint.read_text())
        if (cached.get("schema_version"), cached.get("size_bytes"), cached.get("mtime_ns"), cached.get("preview_count")) == (SCHEMA_VERSION, stat.st_size, stat.st_mtime_ns, number):
            if all((record_dir / name).exists() for name in ("previews.jpg", "fill_labels.csv", "synchronization.csv")):
                return cached
    counts = Counter()
    bad_stamps = Counter()
    times = {key: [] for key in TOPICS}
    camera = {key: [] for key in ("narrow", "wide")}
    previews = {key: [] for key in camera}
    randoms = {key: random.Random(0) for key in camera}
    fills = []
    errors = []
    reverse_topics = {v: k for k, v in TOPICS.items()}
    with path.open("rb") as stream:
        reader = make_reader(stream, decoder_factories=[DecoderFactory()])
        summary = reader.get_summary()
        topic_counts = Counter()
        if summary and summary.statistics:
            for channel_id, count in summary.statistics.channel_message_counts.items():
                topic_counts[summary.channels[channel_id].topic] += count
        selected = {view: preview_indices(topic_counts.get(TOPICS[view], 0), number) for view in camera}
        for _, channel, _, msg in reader.iter_decoded_messages(topics=list(TOPICS.values()), log_time_order=False):
            view = reverse_topics[channel.topic]
            index = counts[view]
            counts[view] += 1
            try:
                ts = stamp_ns(msg)
                times[view].append(ts)
            except (AttributeError, ValueError, TypeError):
                ts = None
                bad_stamps[view] += 1
            if view == "fill":
                try:
                    value = float(msg.data)
                except (ValueError, TypeError, AttributeError):
                    value = None
                fills.append({"fill_index": index, "fill_timestamp_ns": ts, "fill_level": value})
                continue
            if ts is not None:
                camera[view].append({"timestamp_ns": ts, "index": index})
            slot = None
            if selected[view]:
                if index in selected[view]:
                    slot = len(previews[view])
            else:
                # No MCAP summary: deterministic reservoir, O(number) image memory.
                candidate = index if index < number else randoms[view].randrange(index + 1)
                if candidate < number:
                    slot = candidate
            if slot is not None:
                try:
                    im, error = thumb(bytes(msg.data)), ""
                except Exception as exc:
                    im, error = None, str(exc)
                    errors.append({"view": view, "index": index, "error": error})
                item = {"index": index, "timestamp_ns": ts, "image": im, "error": error}
                if slot == len(previews[view]):
                    previews[view].append(item)
                else:
                    previews[view][slot] = item
    arrays = {}
    for view in camera:
        camera[view].sort(key=lambda x: (x["timestamp_ns"], x["index"]))
        arrays[view] = [x["timestamp_ns"] for x in camera[view]]
    sync = []
    statuses = Counter()
    for fill in fills:
        row = {"source_uid": uid, "recording_id": recording_id, **fill}
        value, ts = fill["fill_level"], fill["fill_timestamp_ns"]
        if value is None or not math.isfinite(value) or not 0 <= value <= 100:
            status = "invalid_fill_level"
        elif ts is None:
            status = "invalid_fill_timestamp"
        else:
            status = "synchronized_candidate"
            for view in camera:
                match = nearest(ts, camera[view], arrays[view])
                if match is None:
                    status = "missing_camera_timestamps"
                    continue
                delta_ns = match["timestamp_ns"] - ts
                row.update({f"{view}_index": match["index"], f"{view}_timestamp_ns": match["timestamp_ns"], f"{view}_signed_delta_seconds": delta_ns / 1e9})
                if abs(delta_ns) > 1_000_000_000 and status != "missing_camera_timestamps":
                    status = "outside_sync_tolerance"
        row["status"] = status
        statuses[status] += 1
        sync.append(row)
    sync_fields = ["source_uid", "recording_id", "fill_index", "fill_timestamp_ns", "fill_level", "status"]
    for view in camera:
        sync_fields += [f"{view}_index", f"{view}_timestamp_ns", f"{view}_signed_delta_seconds"]
    write_csv(record_dir / "fill_labels.csv", fills, ["fill_index", "fill_timestamp_ns", "fill_level"])
    write_csv(record_dir / "synchronization.csv", sync, sync_fields)
    contact_sheet(record_dir / "previews.jpg", relative, previews, number)
    valid = [r["fill_level"] for r in fills if r["fill_level"] is not None and math.isfinite(r["fill_level"]) and 0 <= r["fill_level"] <= 100]
    accepted = [r for r in sync if r["status"] == "synchronized_candidate"]
    pairs = Counter((r["narrow_index"], r["wide_index"]) for r in accepted)
    stats = summary.statistics if summary else None
    result = {
        "schema_version": SCHEMA_VERSION, "source_uid": uid, "recording_id": recording_id,
        "source_mcap": relative, "size_bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns,
        "preview_count": number, "scan_status": "complete", "filename_lighting_hint": "night" if "night" in relative.lower() else "unspecified",
        "lighting_review": "pending", "capture_week": "", "capture_session": "",
        "fill_messages": counts["fill"], "narrow_messages": counts["narrow"], "wide_messages": counts["wide"],
        "valid_fill_labels": len(valid), "synchronized_candidates": len(accepted),
        "rejected_before_visual_qc": len(sync) - len(accepted), "rejection_counts": dict(statuses),
        "reused_camera_pairs": sum(n - 1 for n in pairs.values()), "invalid_header_counts": dict(bad_stamps),
        "preview_decode_errors": len(errors), "preview_error_details": errors,
        "fill_min": min(valid) if valid else None, "fill_max": max(valid) if valid else None,
        "fill_mean": sum(valid) / len(valid) if valid else None,
        "raw_bins": [sum(lo <= v < hi for v in valid) for lo, hi in [(0,10),(10,20),(20,30),(30,40),(40,50),(50,60),(60,70),(70,80),(80,90),(90,101)]],
        "sync_bins": [sum(lo <= r["fill_level"] < hi for r in accepted) for lo, hi in [(0,10),(10,20),(20,30),(30,40),(40,50),(50,60),(60,70),(70,80),(80,90),(90,101)]],
        "observed_log_start_utc": utc(stats.message_start_time) if stats else "",
        "observed_log_end_utc": utc(stats.message_end_time) if stats else "",
        "previous_v2_exclusion": "tiny_recording" if path.name == "2026_08_22-13_10_54_eye_0.mcap" else "",
        "preview_path": (record_dir / "previews.jpg").relative_to(output).as_posix(),
    }
    for key, values in times.items():
        result[f"observed_{key}_header_start_utc"] = utc(min(values)) if values else ""
        result[f"observed_{key}_header_end_utc"] = utc(max(values)) if values else ""
        result[f"{key}_header_backwards_steps"] = sum(b < a for a, b in zip(values, values[1:]))
    tmp = checkpoint.with_suffix(".tmp")
    tmp.write_text(json.dumps(result, indent=2), encoding="utf-8")
    tmp.replace(checkpoint)
    return result


def finish(output, results):
    import html
    fields = ["source_uid", "recording_id", "source_mcap", "scan_status", "filename_lighting_hint", "lighting_review", "capture_week", "capture_session", "fill_messages", "valid_fill_labels", "narrow_messages", "wide_messages", "synchronized_candidates", "rejected_before_visual_qc", "reused_camera_pairs", "preview_decode_errors", "fill_min", "fill_max", "fill_mean", "observed_fill_header_start_utc", "observed_fill_header_end_utc", "observed_narrow_header_start_utc", "observed_narrow_header_end_utc", "observed_wide_header_start_utc", "observed_wide_header_end_utc", "observed_log_start_utc", "observed_log_end_utc", "previous_v2_exclusion", "preview_path"]
    write_csv(output / "inventory.csv", [{k:r.get(k, "") for k in fields} for r in results], fields)
    write_csv(output / "lighting_review_template.csv", [{"source_uid":r["source_uid"], "source_mcap":r["source_mcap"], "lighting":"pending", "reviewer":"", "capture_week":"", "capture_session":"", "notes":""} for r in results], ["source_uid", "source_mcap", "lighting", "reviewer", "capture_week", "capture_session", "notes"])
    parts = ["<!doctype html><html><meta charset='utf-8'><title>MCAP lighting review</title><style>body{font:16px system-ui;margin:24px;background:#eee}section{background:white;padding:18px;margin:24px 0}img{max-width:100%;height:auto}h2{overflow-wrap:anywhere}</style><h1>MCAP lighting review</h1><p>Previews sample the recording; they do not prove full-recording lighting or image quality. Filename hints are unverified. Mixed/uncertain recordings need further inspection. Fill times are observed ROS header UTC, not confirmed collection dates.</p>"]
    for r in results:
        parts.append(f"<section><h2>{html.escape(r['source_mcap'])}</h2><p>Scan: {r.get('scan_status')} | Filename hint: {r.get('filename_lighting_hint','')} | Raw labels: {r.get('fill_messages','')} | Synchronized candidates: {r.get('synchronized_candidates','')} | Header: {r.get('observed_fill_header_start_utc','')} to {r.get('observed_fill_header_end_utc','')}</p>")
        if r.get("preview_path"):
            parts.append(f"<a href='{html.escape(r['preview_path'])}'><img loading='lazy' src='{html.escape(r['preview_path'])}'></a>")
        parts.append("</section>")
    (output / "review.html").write_text("\n".join(parts)+"</html>", encoding="utf-8")
    completed = [r for r in results if r["scan_status"] == "complete"]
    totals = {"sources":len(results), "completed":len(completed), "errors":len(results)-len(completed), "raw_labels_all_lighting":sum(r["fill_messages"] for r in completed), "synchronized_candidates_all_lighting":sum(r["synchronized_candidates"] for r in completed), "visual_qc_status":"pending", "lighting_status":"pending", "week_assignment_status":"unverified"}
    (output / "summary.json").write_text(json.dumps(totals, indent=2), encoding="utf-8")
    print(json.dumps(totals), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=PROJECT / "data")
    parser.add_argument("--output", type=Path, default=PROJECT / "extracted/dataset_audit_v3")
    parser.add_argument("--previews", type=int, default=8)
    args = parser.parse_args()
    if args.previews < 2:
        parser.error("Use at least two previews per camera")
    args.output.mkdir(parents=True, exist_ok=True)
    files = sorted(args.data_dir.rglob("*.mcap"))
    if not files:
        parser.error("No MCAP files found")
    results = []
    for i, path in enumerate(files, 1):
        print(f"[{i}/{len(files)}] {path.name}", flush=True)
        try:
            result = scan(path, args.data_dir, args.output, args.previews)
            print(f"  labels={result['fill_messages']} sync={result['synchronized_candidates']} header={result['observed_fill_header_start_utc']}", flush=True)
        except Exception as exc:
            relative, recording_id, uid = source_identity(path, args.data_dir)
            result = {"source_uid":uid, "recording_id":recording_id, "source_mcap":relative, "scan_status":"error", "error":repr(exc)}
            print(f"  ERROR: {exc}", flush=True)
        results.append(result)
    finish(args.output, results)
    if any(r["scan_status"] == "error" for r in results):
        (args.output / "errors.json").write_text(json.dumps([r for r in results if r["scan_status"]=="error"], indent=2))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
