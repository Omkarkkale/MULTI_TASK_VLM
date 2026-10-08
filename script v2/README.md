# Expanded dataset scripts

The v3 pipeline scripts live here; the older workflow remains in `scripts/`.

## Manual obstruction review

First inspect camera-pair synchronization using:

```bash
python3 "script v2/analyze_camera_sync.py"
```

This writes `camera_sync_analysis/report.md`, a JSON report, and per-sample and
per-recording measurements under the candidate dataset. It does not select a
cutoff. To activate an agreed cutoff, supply `--max-pair-ms` with that value in
milliseconds. Both image-to-GT offsets must still be <= 1 second.

Activating a cutoff creates `sync_policy.json`, `sync_accepted.csv` and
`sync_rejected.csv`. The original `metadata.csv` remains the complete extraction
inventory. Rerun `prepare_v3_review.py` and `review_obstructions.py` after activation
to refresh the proposed counts and viewer. The timestamps are compared as integer
nanoseconds; equality at the cutoff passes. No images are rematched or deleted.

From a Mac terminal:

```bash
cd /Users/omkarkale/thesis_vlm
python3 "script v2/review_obstructions.py"
open extracted/crusher_dataset_v3_candidates/obstruction_review.html
```

This displays all 7,576 currently exported sample pairs, one at a time, with
**front narrow on the left and front wide on the right**. On small screens the
views stack vertically. Click an image for full resolution.

When a synchronization policy is active, the reviewer initially shows only passing
pairs. Uncheck “Within synchronization limit only” to inspect excluded pairs.
Every displayed sample shows its measured camera-to-camera gap and the active
cutoff. Synchronization failures cannot be marked keep in this viewer. Existing
browser decisions are retained, but the filtering script rechecks their timestamps.

- Inspect the crusher opening/fill region in both images.
- If a vehicle or object blocks that region in either camera, reject the whole
  pair using the narrow/wide/both obstruction button.
- If another defect makes the pair unusable, enter a reason and select “Reject —
  other defect.” Leave uncertain samples pending for another look.
- Mark “Keep” only when both views are usable. A truck away from the relevant
  fill region does not automatically make the pair unusable.
- Confirm lighting separately. A keep decision does not approve daylight/night
  classification. Pending, transition and uncertain lighting stay out of the
  daylight/night candidate manifests.
- Use recording and review-status filters, arrow navigation, K to keep, U to undo,
  or disable automatic advance. Keyboard shortcuts apply when focus is outside
  form controls.
- Download the CSV and a JSON backup. Save the CSV as
  `extracted/crusher_dataset_v3_candidates/review_decisions.csv`.

The page shares browser-local decisions with `review.html`. Use one review page
at a time and reload when switching, to avoid overwriting decisions held in an
older open tab. Exported backups are needed to transfer decisions across browsers.

## Exclude rejected and unreviewed samples

After saving the decisions CSV:

```bash
python3 "script v2/apply_visual_qc.py" \
  --decisions extracted/crusher_dataset_v3_candidates/review_decisions.csv
```

No container or third-party Python packages are needed for these two scripts.
The filter requires an active `sync_policy.json` and recomputes all three time
differences from the stored header stamps before accepting any sample. A manual
keep cannot override a synchronization rejection.
Each filter run creates a new timestamped directory under `qc_results/`:

| File | Contents |
| --- | --- |
| `visual_keep.csv` | Explicitly kept, successfully decoded pairs |
| `rejected.csv` | Rejected pairs with reasons |
| `sync_rejected.csv` | Pairs outside the active timestamp limits, regardless of manual QC |
| `pending_qc.csv` | Unreviewed pairs, excluded from kept candidates |
| `daylight_candidates.csv` | Kept pairs with confirmed daylight lighting |
| `night_candidates.csv` | Kept pairs with confirmed night lighting |
| `lighting_hold.csv` | Kept pairs still needing a lighting decision |
| `decisions_applied.csv` | Exact input decisions for this run |
| `summary.json` | Counts, input checksums and release status |

These manifests are candidates for the next split step, not training-ready frozen
datasets. Source images and old dataset versions are preserved. Remaining work:
review held samples, confirm recording/session separation, apply the agreed
chronological split, report final split percentages and fill distributions, and
freeze. Never use the unfiltered source `metadata.csv` as the clean training set.

See [the v3 report](../Documentation/01_Dataset/v3_audit_report.md) for the scan,
export and proposed split details.

## 0–5% nearby-image pilot

`pilot_low_fill_pairs.py` creates a pandas table and image review page for a small
exploration: five nearby pairs per training GT event, one per validation/test event.
It does not copy labels to extra frames or modify the current dataset.
The completed first run is in `extracted/low_fill_pilot_v1/`.

See [the pilot report](../Documentation/01_Dataset/low_fill_pilot_v1.md) for counts,
GT evidence, timestamp sensitivity, split percentages and commands.
