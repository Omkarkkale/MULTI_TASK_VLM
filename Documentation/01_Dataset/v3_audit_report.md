# Dataset v3: current MCAP audit and candidate preparation

Run date: 2026-09-24. Status: candidate extraction and review preparation; **not frozen or approved for training**.

## Camera-to-camera synchronization follow-up

The 7,576 independently matched pairs were subsequently measured using the stored
ROS header timestamps. **None has identical narrow/wide timestamps.** Median gap:
401.525 ms; 95th percentile: 1,319.196 ms; maximum: 1,960.111 ms. These measurements
refer to the selected pairs; alternative frames in the raw MCAPs have not been
searched for closer matches.

An additional camera-pair limit is now supported by `script v2/analyze_camera_sync.py`.
The cutoff is selected separately from the unchanged <= 1 second image-to-GT limits.
At 100 ms, 1,114 total candidates remain (705 train / 15 validation / 153 daylight
test candidates). At 250 ms, 2,112 remain (923 train / 305 validation / 302 daylight
test candidates). Night and lighting-hold samples account for the remaining totals.

The measured comparison and, once chosen, the applied cutoff and updated split
percentages/ranges are in the
[camera synchronization report](../../extracted/crusher_dataset_v3_candidates/camera_sync_analysis/report.md).
The original counts below describe extraction before this additional filter.
`sync_policy.json`, when present, defines the active rule. The QC filtering script
recomputes the rule and excludes failed pairs even if they were manually marked keep.
The focused obstruction viewer displays the pair gap and filters passing pairs.

Header timestamp closeness does not prove simultaneous exposures or accurate clock
calibration. A cutoff is an explicit engineering constraint; adequacy for fast
crusher/vehicle motion still needs validation.

## Measured inventory

All 49 MCAP files currently under `data/` were read using the container's MCAP ROS2 decoder. Results are in [`extracted/dataset_audit_v3`](../../extracted/dataset_audit_v3/).

| Stage | Count |
| --- | ---: |
| MCAPs scanned successfully | 49 |
| Raw fill-level labels, all lighting | 7,638 |
| Labels passing both camera synchronization checks | 7,576 |
| Rejected: camera timestamp difference over 1.0 s | 49 |
| Rejected: no camera timestamps (recording 0) | 13 |
| Invalid ROS header timestamps encountered on the three inspected topics | 0 |
| Repeated camera-ordinal pairs within a source among synchronized candidates | 0 |
| Exported pairs with both images fully decoded | 7,576 |
| Candidate pairs rejected during image decoding | 0 |
| Duplicate encoded image-pair hashes across exported candidates | 0 |

Export results: [`summary.json`](../../extracted/crusher_dataset_v3_candidates/summary.json).
Candidate distribution and exact-pair duplicate analysis:
[`candidate_quality_report.json`](../../extracted/crusher_dataset_v3_candidates/candidate_quality_report.json).
The checksum comparison does not detect visually similar frames or establish session independence.

One sample means **one fill label with two camera images**. Two images do not count as two training samples. Even before lighting exclusions and visual QC, the available labels cannot produce 10,000 distinct synchronized samples: the absolute shortfall is 2,424. Proceed with the available data and report the final clean count honestly.

The earlier 44-file inventory's “normal” designation was based on filenames and hard-coded documentation output. It is not a visual confirmation. The new audit reads the files and preserves filename hints separately from observed lighting.

## Synchronization and extraction

`script v2/audit_mcap_dataset.py` reads these topics:

- `/processing/crusher/fill_level`
- `/sensor/camera/front_narrow/image_raw/compressed/throttled`
- `/sensor/camera/front_wide/image_raw/compressed/throttled`

It uses integer nanoseconds from `header.stamp`, checks finite fill values in [0, 100], finds the nearest image in each camera stream, and requires **each image-to-label difference <= 1.0 s**. This condition permits an inter-camera difference of up to 2.0 s; it does not impose an additional camera-to-camera threshold. Signed differences, timestamps and message ordinals are saved for inspection.

`script v2/export_audited_candidates.py` streams the selected image messages again, checks their ordinals against the audited timestamps, fully decodes each selected image, saves the original encoded bytes, and records image SHA256 checksums. It writes only to `extracted/crusher_dataset_v3_candidates/`. Sample IDs include the source identity and original fill-message ordinal, avoiding filename collisions between the night recordings. Source identity is derived from the relative path; it is **not** a raw-file content checksum. Resume checks use size/mtime and audit metadata, so immutable source checksums are still required at freeze time.

All candidate rows retain `lighting=pending`, `visual_qc=pending` and `split=unassigned`. A successful decode is not a visual-QC approval. The old v2 and night v1 exports are historical artifacts; do not append them to v3, because their raw recordings are already included in this scan.

## Sampled lighting assessment

Eight evenly spaced temporal previews per camera were generated per recording where images exist. All 48 usable recordings were visually inspected through wide-camera overview sheets. Additional full both-camera preview sheets were inspected for recordings 123, 124 and 221. These are **provisional recording-level suggestions**, not a review of all 7,576 synchronized samples.

| Suggested category | MCAPs | Synchronized candidates before QC |
| --- | ---: | ---: |
| Daylight candidate | 33 | 5,458 |
| Night candidate | 5 | 637 |
| Dawn/dusk/transition review | 10 | 1,481 |
| Unusable recording 0 | 1 | 0 |

Night candidates: **101, 125, 221, 245, 412**. The last three have no night filename suffix.

Transition review: **37, 51, 75, 76, 99, 100, 123, 124, 373, 446**. This deliberately includes uncertain boundaries such as early daylight/sunrise in 446. Recordings 37 and 100 have night filenames but contain lighting transitions. Recording 38 also has a night filename, yet its sampled views appear naturally lit; confirm every retained sample before moving it into the daylight dataset. Recording 75 was previously used in v2 training and shows a dusk transition in the new previews.

Suggestions and evidence are saved in [`lighting_assessment.csv`](../../extracted/dataset_audit_v3/lighting_assessment.csv). The automated scanner does not overwrite that assessment file. `lighting_review_template.csv` is regenerated by each audit run; save reviewer changes in a separate file.

## Agreed chronological split

The user selected a **three-week chronological split** after the scan showed only three calendar weeks with usable pairs. Recording 0 is from August 22 but contributes no synchronized samples. MCAP filenames share an August 22 prefix; use observed ROS header timestamps for the provisional chronology.

| Role, daylight only | Observed UTC date range | Daylight-candidate MCAPs | Candidates before full QC |
| --- | --- | ---: | ---: |
| Train | Aug 24–30, 2026 | 19 | 3,423 |
| Validation | Aug 31–Sep 6, 2026 | 9 | 1,366 |
| Test-normal | Sep 7–13, 2026 | 5 | 669 |

These counts exclude all transition-review recordings and all night candidates. They will change after sample QC and lighting decisions. They are not final split sizes.

Confirm recorder clock dates against collection/session records before freezing. UTC is the recorded timestamp basis, not a claim about the collection site's timezone. Group related recordings and sessions; avoid putting neighboring or duplicate views of the same event in different roles. A transitioning source must not contribute daylight to training and related night frames to testing. Keep it on hold, or assign its related samples together to a suitable held-out role after review.

The agreed rule is saved in [`split_plan.json`](../../extracted/crusher_dataset_v3_candidates/split_plan.json). `review_template.csv` supplies the date-derived daylight role and provisional category separately from final decisions.

## Fill distribution that needs attention

The following counts are from the 33 provisional daylight sources, before full sample QC. Bins include the lower bound and exclude the upper bound, except 90–100 includes 100.

| Fill level | Train candidates | Validation candidates | Test-normal candidates |
| --- | ---: | ---: | ---: |
| 0–10 | 96 | **0** | 39 |
| 10–20 | 161 | 28 | 26 |
| 20–30 | 244 | 37 | 27 |
| 30–40 | 383 | 57 | 25 |
| 40–50 | 307 | 234 | 39 |
| 50–60 | 355 | 102 | 30 |
| 60–70 | 656 | 158 | 80 |
| 70–80 | 493 | 183 | 86 |
| 80–90 | 228 | 353 | 95 |
| 90–100 | 500 | 214 | 222 |

The temporal split is feasible, but its distributions differ. In particular, current daylight validation candidates contain **no labels below 10%**. The sampled night-candidate pool contains no labels below 30%, so a pure-night score will not measure performance across the full fill range. Recalculate these tables after QC. Preserve temporal grouping; do not move selected test samples into validation to repair the histogram. Report counts and errors per fill bin in addition to overall error. Any training resampling must be confined to training and must not be counted as additional unique data.

## Review workflow

For a focused obstruction check, use the newer
[`obstruction_review.html`](../../extracted/crusher_dataset_v3_candidates/obstruction_review.html).
It shows one synchronized pair at a time, with labelled narrow/wide views,
full-resolution links, obstruction buttons for each camera, and undo.
Generate it with `python3 "script v2/review_obstructions.py"` from the project root.
After exporting decisions, `script v2/apply_visual_qc.py` creates separate kept,
rejected and pending manifests, with daylight/night candidates separated by
explicit lighting decisions. Instructions are in
[`script v2/README.md`](../../script%20v2/README.md).
Full manual review and final split generation remain pending.

Open [`extracted/crusher_dataset_v3_candidates/review.html`](../../extracted/crusher_dataset_v3_candidates/review.html) in a browser. The page displays the synchronized narrow/wide pair, fill label, timestamp and suggested lighting, with recording filters and pagination.

For each candidate:

1. Confirm both images show the relevant crusher fill region. Reject obstruction of that region, corrupt/unusable imagery, or apparent label/image mismatches. A visible truck elsewhere alone does not require rejection.
2. Mark lighting as `daylight`, `night`, `transition` or `uncertain`. Pending/transition/uncertain samples are not eligible for the normal training or validation set.
3. Mark QC `keep` or `reject`, and record a reason for rejection.
4. Download the decisions CSV to this dataset folder as `review_decisions.csv`. Download the JSON backup to preserve/restore page decisions. Browser-local storage is a convenience, not the authoritative review artifact.

This page does not create final splits or approve samples automatically. Full sample review remains pending. The old 15 hard-coded v2 obstruction exclusions must not be reused by sample counter without matching them to the new source timestamps/ordinals.

After review: join decisions to metadata by `sample_id`, preserve a complete rejection log, confirm lighting/session groups, check duplicate image content across roles, recompute split distributions, then write and freeze the versioned manifests. The source and image checksums, parameters, script versions and QC decisions belong in that freeze.

## Final model evaluations

- Exp 1: approved daylight test-normal only.
- Exp 2: a fixed, documented mixture drawn only from approved test-normal and test-night samples. Publish the mixture proportion and report both lighting subsets as well as the combined score. This experiment reuses test pools; it is not a third independent collection.
- Exp 3: approved night test samples only.

Select the model using daylight validation only; freeze model, prompts, preprocessing and thresholds before these tests. Night samples do not enter training or validation.

## Commands from a new Mac terminal

With `thesis-vlm-dev` running:

```bash
cd /Users/omkarkale/thesis_vlm
docker exec thesis-vlm-dev python3 "/workspace/script v2/audit_mcap_dataset.py"
docker exec thesis-vlm-dev python3 "/workspace/script v2/create_audit_overviews.py"
docker exec thesis-vlm-dev python3 "/workspace/script v2/export_audited_candidates.py"
docker exec thesis-vlm-dev python3 "/workspace/script v2/prepare_v3_review.py"
open extracted/crusher_dataset_v3_candidates/review.html
```

The export requires `lighting_assessment.csv`, which records the sampled visual review performed for the current 49 files. When adding new MCAPs, rerun the audit, visually assess the new sources, and extend this file before export. Keep existing reviewer decisions separately from regenerated templates. All scripts use the MCAP/Pillow dependencies already available in the container.

Do not use the legacy v2 exporter/split scripts to build v3: their output paths, filename parsing or recording lists assume the earlier dataset.
