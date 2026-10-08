"""Stream audited camera pairs to an UNSPLIT v3 candidate dataset for visual QC.

Uses source-local message ordinals from audit_mcap_dataset.py. Decode checks and
SHA256 checksums cover every selected image. Does not approve QC or assign splits.
"""
import csv
import hashlib
from io import BytesIO
import json
from pathlib import Path

from audit_mcap_dataset import PROJECT, TOPICS, stamp_ns, write_csv


def export_source(audit, audit_root, output, assessment):
    from mcap.reader import make_reader
    from mcap_ros2.decoder import DecoderFactory
    from PIL import Image

    source = PROJECT / "data" / audit["source_mcap"]
    stat = source.stat()
    if (stat.st_size, stat.st_mtime_ns) != (audit["size_bytes"], audit["mtime_ns"]):
        raise ValueError(f"Source changed since audit: {source}")
    sync_path = audit_root / "recordings" / audit["source_uid"] / "synchronization.csv"
    rows = [r for r in csv.DictReader(sync_path.open()) if r["status"] == "synchronized_candidate"]
    destination = output / "recordings" / audit["source_uid"]
    destination.mkdir(parents=True, exist_ok=True)
    cache_path = destination / "export.json"
    signature = hashlib.sha256(sync_path.read_bytes()).hexdigest()
    if cache_path.exists():
        cache = json.loads(cache_path.read_text())
        if cache.get("synchronization_sha256") == signature and cache.get("source_mtime_ns") == stat.st_mtime_ns:
            cached_rows = list(csv.DictReader((destination / "metadata.csv").open()))
            if all((output / r[f"{v}_image"]).is_file() for r in cached_rows for v in ("narrow", "wide") if r.get(f"{v}_image")):
                return cached_rows
        raise ValueError(f"Existing export differs; use a new output directory: {destination}")
    wanted = {v: {int(r[f"{v}_index"]): int(r[f"{v}_timestamp_ns"]) for r in rows} for v in ("narrow", "wide")}
    images = {v: {} for v in wanted}
    counts = {v: 0 for v in wanted}
    reverse = {TOPICS[v]: v for v in wanted}
    if rows:
        with source.open("rb") as stream:
            reader = make_reader(stream, decoder_factories=[DecoderFactory()])
            for _, channel, _, message in reader.iter_decoded_messages(topics=list(reverse), log_time_order=False):
                view = reverse[channel.topic]
                index = counts[view]
                counts[view] += 1
                if index not in wanted[view]:
                    continue
                if stamp_ns(message) != wanted[view][index]:
                    raise ValueError(f"Camera ordinal/timestamp mismatch: {source} {view} {index}")
                try:
                    data = bytes(message.data)
                    with Image.open(BytesIO(data)) as im:
                        im.load()
                        if im.format not in ("JPEG", "PNG"):
                            raise ValueError(f"Unsupported source format: {im.format}")
                        suffix = ".jpg" if im.format == "JPEG" else ".png"
                        width, height = im.size
                    path = destination / f"{view}_{index:06d}{suffix}"
                    temporary = path.with_suffix(path.suffix + ".tmp")
                    temporary.write_bytes(data)
                    temporary.replace(path)
                    images[view][index] = {"image": path.relative_to(output).as_posix(), "sha256": hashlib.sha256(data).hexdigest(), "width": width, "height": height, "decode_error": ""}
                except Exception as exc:
                    images[view][index] = {"image": "", "sha256": "", "width": "", "height": "", "decode_error": str(exc)}
    for row in rows:
        row["sample_id"] = f"{audit['source_uid']}_fill_{int(row['fill_index']):06d}"
        row["source_mcap"] = audit["source_mcap"]
        row["suggested_lighting"] = assessment.get("suggested_lighting", "pending")
        row["lighting"] = "pending"
        row["visual_qc"] = "pending"
        row["split"] = "unassigned"
        row["capture_session"] = ""
        row["capture_week"] = ""
        for view in wanted:
            info = images[view].get(int(row[f"{view}_index"]), {"image": "", "sha256": "", "width": "", "height": "", "decode_error": "Selected frame not encountered"})
            row.update({f"{view}_{key}": value for key, value in info.items()})
        row["export_status"] = "decoded_candidate" if not row["narrow_decode_error"] and not row["wide_decode_error"] else "decode_rejected"
    fields = list(rows[0]) if rows else ["sample_id", "export_status"]
    write_csv(destination / "metadata.csv", rows, fields)
    cache_path.write_text(json.dumps({"synchronization_sha256": signature, "source_mtime_ns": stat.st_mtime_ns, "candidate_rows": len(rows), "decoded_candidates": sum(r["export_status"] == "decoded_candidate" for r in rows)}, indent=2))
    return rows


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", type=Path, default=PROJECT / "extracted/dataset_audit_v3")
    parser.add_argument("--output", type=Path, default=PROJECT / "extracted/crusher_dataset_v3_candidates")
    args = parser.parse_args()
    assessments = {r["source_uid"]: r for r in csv.DictReader((args.audit / "lighting_assessment.csv").open())}
    audits = [json.loads(p.read_text()) for p in sorted((args.audit / "recordings").glob("*/audit.json"))]
    args.output.mkdir(parents=True, exist_ok=True)
    all_rows = []
    for index, audit in enumerate(audits, 1):
        print(f"[{index}/{len(audits)}] {audit['source_uid']}", flush=True)
        rows = export_source(audit, args.audit, args.output, assessments.get(audit["source_uid"], {}))
        all_rows.extend(rows)
        print(f"  exported {len(rows)} rows", flush=True)
    if all_rows:
        write_csv(args.output / "metadata.csv", all_rows, list(all_rows[0]))
    totals = {"sources": len(audits), "synchronized_candidates": len(all_rows), "decoded_candidates": sum(r["export_status"] == "decoded_candidate" for r in all_rows), "decode_rejected": sum(r["export_status"] != "decoded_candidate" for r in all_rows), "lighting_status": "pending", "visual_qc_status": "pending", "split_status": "unassigned", "frozen": False}
    (args.output / "summary.json").write_text(json.dumps(totals, indent=2))
    print(json.dumps(totals), flush=True)


if __name__ == "__main__":
    main()
