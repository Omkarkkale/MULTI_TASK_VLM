"""Initialize v3 QC from user-reported recording rejection and exact v2 matches.

Only writes audit manifests under results/. Raw dataset images/metadata are read
only. Unreviewed samples are pending, never automatically approved as clean.
"""
import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]


def read_rows(path):
    with path.open(newline='', encoding='utf-8-sig') as stream:
        return list(csv.DictReader(stream))


def write_rows(path, rows, fields):
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def timestamp_key(row):
    return (str(row['recording_id']), int(row['fill_timestamp_ns']),
            int(row['narrow_timestamp_ns']), int(row['wide_timestamp_ns']))


def sample_key(row):
    return (str(row['recording_id']), int(row['sample']))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=PROJECT/'results/crusher_dataset_v3_qc')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output already exists; use a new --output to preserve review decisions')
    v2 = PROJECT/'extracted/crusher_dataset_v2'
    v3 = PROJECT/'extracted/crusher_dataset_v3'
    inputs = [v2/'master_metadata.csv', v2/'rejected_samples.csv', v3/'master_metadata.csv']
    input_checksums = {str(p.relative_to(PROJECT)): digest(p) for p in inputs}
    old_rows, legacy_rejections, rows = (read_rows(p) for p in inputs)
    old_lookup = {sample_key(r): r for r in old_rows}
    if len(old_lookup) != len(old_rows) or len({sample_key(r) for r in rows}) != len(rows):
        parser.error('Duplicate recording/sample identity in source metadata')
    target_lookup = defaultdict(list)
    for row in rows:
        target_lookup[timestamp_key(row)].append(row)
    legacy_evidence, verified = [], {}
    for rejection in legacy_rejections:
        old = old_lookup.get(sample_key(rejection))
        candidates = target_lookup[timestamp_key(old)] if old else []
        evidence = {'recording_id': rejection['recording_id'], 'v2_sample': rejection['sample'],
                    'v3_sample': '', 'match_status': 'unresolved', 'reason': rejection['reason'],
                    'fill_timestamp_ns': old['fill_timestamp_ns'] if old else '',
                    'narrow_timestamp_ns': old['narrow_timestamp_ns'] if old else '',
                    'wide_timestamp_ns': old['wide_timestamp_ns'] if old else '',
                    'v2_narrow_sha256': '', 'v3_narrow_sha256': '',
                    'v2_wide_sha256': '', 'v3_wide_sha256': '', 'detail': ''}
        if old is None or len(candidates) != 1:
            evidence['detail'] = 'Missing v2 row or no unique v3 timestamp match'
        else:
            target = candidates[0]
            evidence['v3_sample'] = target['sample']
            same = float(old['fill_level']) == float(target['fill_level']) == float(rejection['fill_level'])
            try:
                for view in ('narrow', 'wide'):
                    evidence[f'v2_{view}_sha256'] = digest(v2/old[f'front_{view}'])
                    evidence[f'v3_{view}_sha256'] = digest(v3/target[f'front_{view}'])
                    same = same and evidence[f'v2_{view}_sha256'] == evidence[f'v3_{view}_sha256']
                if same:
                    evidence['match_status'] = 'verified_exact_images_label_and_timestamps'
                    evidence['detail'] = 'Carry forward the documented v2 rejection; no new visual review claimed'
                    verified[sample_key(target)] = evidence
                else:
                    evidence['detail'] = 'Image bytes or GT value differ; manual recheck required'
            except OSError as exc:
                evidence['detail'] = str(exc)
        legacy_evidence.append(evidence)
    now = datetime.now(timezone.utc).isoformat()
    record_counts = Counter(r['recording_id'] for r in rows)
    if '121' not in record_counts:
        parser.error('Recording 121 not present in source v3 metadata')
    recording_reviews = []
    for rid in sorted(record_counts, key=int):
        rejection = rid == '121'
        recording_reviews.append({'recording_id': rid, 'synchronized_samples': record_counts[rid],
            'recording_qc_status': 'reject_entire_recording' if rejection else 'pending',
            'reason': 'truck_obstructs_relevant_crusher_view_in_all_inspected_samples' if rejection else '',
            'review_source': 'user_reported_visual_review' if rejection else '',
            'review_scope': 'User reported obstruction throughout recording; not independently inspected in this step' if rejection else '',
            'historical_sample_rejections': sum(key[0] == rid for key in verified),
            'recorded_at_utc': now if rejection else ''})
    metadata = []
    for original in rows:
        row = dict(original)
        row.update(qc_status='pending', qc_reason='', qc_scope='', qc_evidence_source='', qc_recorded_at_utc='')
        if row['recording_id'] == '121':
            row.update(qc_status='reject', qc_reason='truck_obstructs_relevant_crusher_view_in_all_inspected_samples',
                       qc_scope='recording', qc_evidence_source='user_reported_visual_review', qc_recorded_at_utc=now)
        elif sample_key(row) in verified:
            evidence = verified[sample_key(row)]
            row.update(qc_status='reject', qc_reason=evidence['reason'], qc_scope='sample',
                       qc_evidence_source=f"v2 rejected_samples.csv; sample {evidence['v2_sample']}; exact image hashes, label and timestamps verified", qc_recorded_at_utc=now)
        metadata.append(row)
    rejected = [r for r in metadata if r['qc_status'] == 'reject']
    pending = [r for r in metadata if r['qc_status'] == 'pending']
    summary = {'status': 'qc_in_progress_not_a_clean_dataset', 'created_at_utc': now,
               'source_synchronized_samples': len(rows), 'source_recordings': len(record_counts),
               'recording_121_rejected': record_counts['121'],
               'historical_rejections_checked': len(legacy_evidence),
               'historical_rejections_verified': len(verified),
               'historical_rejections_unresolved': len(legacy_evidence)-len(verified),
               'total_rejected_samples': len(rejected), 'samples_pending_review': len(pending),
               'approved_clean_samples': 0,
               'rejected_by_recording': dict(Counter(r['recording_id'] for r in rejected)),
               'source_checksums': input_checksums,
               'synchronization_rule': 'Existing GT-to-each-camera <= 1 second; no camera-to-camera filter applied',
               'split_status': 'No train/validation/test split created',
               'image_paths_relative_to': str(v3.relative_to(PROJECT))}
    # Check the source metadata did not change during this read-only preparation.
    if any(digest(p) != input_checksums[str(p.relative_to(PROJECT))] for p in inputs):
        raise RuntimeError('Source metadata changed while preparing QC; no manifests written')
    args.output.mkdir(parents=True)
    write_rows(args.output/'recording_qc_manifest.csv', recording_reviews, list(recording_reviews[0]))
    write_rows(args.output/'v2_rejection_match_evidence.csv', legacy_evidence, list(legacy_evidence[0]) if legacy_evidence else ['recording_id','v2_sample','v3_sample','match_status'])
    fields = list(metadata[0])
    write_rows(args.output/'all_samples_qc_manifest.csv', metadata, fields)
    write_rows(args.output/'rejected_samples.csv', rejected, fields)
    write_rows(args.output/'pending_review_metadata.csv', pending, fields)
    (args.output/'summary.json').write_text(json.dumps(summary, indent=2))
    (args.output/'README.md').write_text(f'''# V3 visual QC — initial decisions

Status: **in progress**. This folder contains review manifests, not a frozen clean dataset.

- Source: {len(rows):,} synchronized samples from {len(record_counts)} recordings.
- Recording 121: {record_counts['121']} rejected based on the user's visual review report.
- Historical v2 exclusions: {len(verified)} verified by exact narrow/wide image hashes,
  GT label, recording ID and all three timestamps. The v2 visual judgment is carried
  forward; no new visual inspection of these pairs is claimed.
- Total rejected: {len(rejected)}.
- Remaining pending review: {len(pending):,}. These are **not yet approved as usable**.
- Approved clean samples: 0. No train/validation/test splits have been created.

## Files

- `recording_qc_manifest.csv`: all recordings; only 121 has a completed recording-level rejection.
- `v2_rejection_match_evidence.csv`: exact-match evidence for historical exclusions.
- `all_samples_qc_manifest.csv`: every source row and its current QC status.
- `rejected_samples.csv`: explicit sample/recording rejections with reasons and provenance.
- `pending_review_metadata.csv`: review queue after these exclusions, not a training manifest.
- `summary.json`: counts, source checksums and status.

Image paths in these CSVs are relative to `extracted/crusher_dataset_v3/`.
The original v3 dataset and v2 files were only read. Images have not been deleted.
The existing ±1-second GT synchronization rule is unchanged; no camera-pair filter
has been activated. Initial recording screening can identify where detailed review
is needed, but a few clear previews do not automatically approve every sample.

Continue visual QC on the 35 pending recordings, including the remaining samples
in 94 and 118. Once QC is complete, generate a separate clean dataset manifest and
report its fill coverage before assigning train/validation/test splits.
''')
    print(json.dumps(summary, indent=2))
    print(f'QC manifests: {args.output}')


if __name__ == '__main__':
    main()
