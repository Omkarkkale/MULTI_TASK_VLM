# Dataset Protocol V3

## Status and scope

- Protocol identifier: `dataset_protocol_v3`
- Protocol specification approved: 2026-09-28
- Purpose: document the implemented sample-generation and manual-QC
  procedure used for the existing visually clean v3 crusher dataset.
- Existing clean baseline: 5,401 paired samples from 34 daylight recordings.
- Additional batches intended for combination with this baseline must
  preserve the sample-generation rules described below.

This document records an approved protocol specification. It does not
freeze a train/validation/test split, create a new dataset release, or
certify new samples as visually clean.

A future dataset release may have a different version name while still
using `dataset_protocol_v3`.

## 1. Implementation provenance

Reference exporter:
`scripts/export_normal_crusher_dataset_v3.py`

Reference QC filter:
`scripts/filter_truck_obstructions_v3.py`

The implementation hashes recorded at document creation appear at the
end of this document. They identify file contents, not execution results.

These hashes identify the exact historical reference-script versions.
A future implementation may have a different hash while remaining
compatible with `dataset_protocol_v3`, provided the sample-generation and
QC semantics defined in this document are preserved.

## 2. Protocol summary

For each decoded crusher fill-level message within an MCAP, the v3
pipeline independently selects the nearest front-narrow and front-wide
camera messages using ROS header timestamps, with exact-distance ties
resolved by first occurrence in the in-memory camera list; one pair is
retained when both absolute camera-to-GT offsets are no greater than
1.0 second, camera-frame reuse is permitted, the target converted to a
Python float and compressed camera bytes are retained without additional
transformation, and manually determined visual-QC exclusions are applied
afterward through separate manifests.

## 3. Input streams and recording boundary

Each MCAP is processed independently.

Required decoded message streams:

- GT: `/processing/crusher/fill_level`
- Narrow: `/sensor/camera/front_narrow/image_raw/compressed/throttled`
- Wide: `/sensor/camera/front_wide/image_raw/compressed/throttled`

If any of these three decoded message collections is empty, the
recording contributes no samples.

Matching does not search across MCAP boundaries.

## 4. Ground truth and timestamps

- The target is read specifically from `ros_msg.data`.
- The target is converted using `float(ros_msg.data)`.
- GT and camera timestamps use `ros_msg.header.stamp`.
- Conversion to integer nanoseconds is:
  `stamp.sec * 1_000_000_000 + stamp.nanosec`.
- No explicit timestamp offset correction is applied.
- No smoothing, intentional rounding, clipping, or binning of the target
  is performed by the exporter.

The reference exporter does not explicitly enforce finite values,
the 0–100 range, or integer-valued targets. These must not be described
as validation checks already implemented by that exporter.

## 5. Camera matching

For each decoded GT event:

1. Find the narrow-camera index minimizing absolute timestamp distance.
2. Independently find the wide-camera index minimizing absolute
   timestamp distance.

Frames before or after the GT timestamp may be selected.

The reference implementation uses:

    min(
        range(len(timestamps)),
        key=lambda i: abs(timestamps[i] - target_ns)
    )

Camera lists are populated in reader iteration order. The exporter does
not explicitly sort them by ROS header timestamp.

For an exact-distance tie, the first corresponding camera-list index
is selected. This must not be described as necessarily selecting the
earlier header timestamp.

There is no joint narrow/wide optimization.

## 6. Timing acceptance and sample multiplicity

Accept an event only when both conditions hold:

- `abs(t_narrow - t_GT) / 1e9 <= 1.0`
- `abs(t_wide - t_GT) / 1e9 <= 1.0`

Exactly 1.0 second is accepted.

There is no independent narrow-to-wide acceptance threshold.
Consequently, accepted camera messages can be up to 2.0 seconds apart.

Each decoded GT event produces at most one accepted pair.

**Camera-frame reuse is allowed.**

Multiple GT events may select the same underlying narrow frame,
wide frame, or both. The exporter can write reused observations into
separately named output files.

Accepted sample count therefore does not guarantee an equal count of
unique camera observations.

Duplicate GT timestamps are not explicitly deduplicated. No temporal
downsampling or fill-range quota is applied during extraction.

## 7. Sample numbering and image export

Accepted-sample numbering starts at 1 independently within each recording.

Example:

    GT message #1 -> rejected by timing
    GT message #2 -> accepted -> sample_0001
    GT message #3 -> accepted -> sample_0002

The `sample` field is the accepted-sample counter, not the source
GT-message ordinal. The source GT ordinal is not saved.

The GT timestamp is retained in `fill_timestamp_ns`; however, timestamps
are not guaranteed to be unique because duplicate GT timestamps are
not explicitly deduplicated.

Camera indices are zero-based positions in the in-memory camera lists.

The exporter writes `CompressedImage.data` bytes directly to `.jpg`
files without decoding, resizing, normalization, re-encoding, or
format validation. A `.jpg` extension is not proof that the exporter
verified JPEG encoding or image integrity.

## 8. Synchronized metadata

The reference exporter writes these columns:

- `recording_id`
- `source_mcap`
- `sample`
- `front_narrow`
- `front_wide`
- `fill_level`
- `fill_timestamp_ns`
- `narrow_camera_index`
- `narrow_timestamp_ns`
- `narrow_delta_t_seconds`
- `narrow_signed_delta_t_seconds`
- `wide_camera_index`
- `wide_timestamp_ns`
- `wide_delta_t_seconds`
- `wide_signed_delta_t_seconds`

Signed deltas use `camera_timestamp - GT_timestamp`, in seconds.

- Positive: camera frame is after GT.
- Negative: camera frame is before GT.

Image paths are relative to the extraction root.

## 9. Manual visual QC

Visual QC occurs after synchronization and image export.

The workflow requires manual review of extracted narrow/wide pairs.
Pairs in which the relevant crusher view is obstructed, or in which an
image is visibly unusable for the intended crusher fill-level task, are
recorded as manual QC exclusions.

The reason for every exclusion must be recorded explicitly. New rejection
criteria must not be introduced silently when processing later batches.

The reference QC script does not inspect images or perform automatic
obstruction detection. It applies explicitly recorded manual decisions.

Filtering order:

1. Recording-level rejection.
2. Otherwise, individual `(recording_id, sample)` rejection.
3. Retain rows matching neither rejection list.

Recording-level rejection takes precedence over sample-level rejection.

Non-rejected rows are retained automatically. The script does not
independently verify that every retained pair was reviewed. Final
visually clean status therefore depends on completion of manual review.

Original sample numbers and image paths are preserved after filtering.

Outputs:

- `master_metadata.csv`: original synchronized metadata, preserved.
- `master_metadata_clean.csv`: retained rows with original columns.
- `rejected_samples.csv`: rejected sample identity, fill value, image
  paths, rejection type, and reason.

The QC filter does not delete source images or modify the original
synchronized master metadata.

Individual recording/sample rejection lists are dataset-specific
decisions. They are not universal exclusions for every future batch.

## 10. Incremental application

For an additional batch:

- Select explicitly identified, manually confirmed DAY recordings.
- Record batch identity, source filename, lighting domain, and the
  provenance of the lighting review in a batch manifest.
- Preserve the matching, acceptance, numbering, and target-handling
  semantics above.
- Write new extraction outputs to a separate batch location.
- Complete visual QC of the new batch before combining clean manifests.
- Preserve the existing 5,401-pair baseline and its QC decisions.

For batch `2026_09_28`, lighting was manually reviewed in Foxglove.
Night recordings were subsequently marked with `night_mcaps` in their
filenames; unmarked recordings were confirmed DAY. Filename markers
record that manual decision rather than automatically discovering
lighting conditions.

The historical exporter selects files from the entire data directory
and writes into the existing v3 output root. It must not be rerun
unchanged to process an incremental batch.

The reference exporter and QC filter use overwrite mode for their
generated outputs. Overwrite protection is an operational improvement,
not a change to which observations constitute valid samples.

## 11. Pre-extraction scan guards and reporting

An incremental raw-label scan may stop on:

- non-finite values;
- values outside the expected 0–100 range;
- fractional values incompatible with the existing integer-bin report;
- unexpected schema or decoding behavior.

These stops require investigation. They do not authorize silently
discarding, rounding, clipping, or otherwise transforming samples.

The established monitoring ranges are:

    0–10, 11–20, 21–30, 31–40, 41–50,
    51–60, 61–70, 71–80, 81–90, 91–100

These inclusive ranges completely cover integer percentages from
0 through 100. They contain gaps for fractional values, so fractional
labels require an explicit reporting-boundary decision before reporting
a complete distribution.

Reporting bins are not model output classes or sample-acceptance rules.

Raw fill-message counts must remain distinct from synchronized-pair
counts and final visually clean counts.

## 12. Change control and evaluation boundary

Changes to topics, timestamp source, matching, tie behavior, timing
tolerance, frame reuse, deduplication, target transformations, sampling
multiplicity, or QC criteria require explicit review and a documented
protocol revision.

Do not silently combine samples generated under different rules as
though they share one protocol. A changed protocol requires an explicit
comparability strategy, such as reprocessing the affected data.

Operational improvements may include batch manifests, duplicate checks,
file-existence checks, separate output directories, and clearer error
messages, provided they do not silently alter sample-generation semantics.

A collection target of 500 or 1,000 clean pairs per range concerns data
coverage. It does not change sample validity.

Benchmark protocols separately define evaluation data, model versions,
prompts, inference settings, output parsing, and metrics. This document
does not freeze those choices or establish a train/validation/test split.

## 13. Reference implementation SHA-256 hashes

- Exporter: `79c2bc96b6814bc33a90e07a3226d787e9ce1e4aa74412ca39e3cf77cdbd3f20`
- QC filter: `8f9fdfdc33b6cfb9b91d33b5a62733bf8c8e3d1914c952ba2d04a1a738a2026b`
