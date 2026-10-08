# 0–5% bucket: nearby-image pilot

Date: September 24, 2026. **Exploratory only; no extra training labels assigned.**

## What was built

`script v2/pilot_low_fill_pairs.py` uses pandas and reads the two relevant raw
MCAPs. It selects GT values in **[0,5)**, meaning 0% is included and 5% belongs to
the next bucket. It exports up to five distinct narrow/wide pairs per Week 1 GT
event and one per validation/test GT event.

Selection uses the closest five frames in each camera, ranks combinations by
maximum distance to GT, then total distance to GT, then camera gap, and greedily
selects pairs without reusing either camera frame within that GT event. This is
an exploration of nearby images, not an optimized search for all possible tightly
synchronized pairs. All 88 original selected pairs are represented in the output.

The table includes GT value and time, both image times and paths, pair rank,
image-to-GT offsets, camera-pair gap, preceding/following GT readings, bracketing
GT evidence, duplicate/reuse counts, and explicit pending-review fields.
The GT value is an anchor measurement, **not an automatically propagated label**.

## Results

| Period | Recording | GT events | Diagnostic pairs | Pairs within both GT ±1 s limits |
| --- | --- | ---: | ---: | ---: |
| Week 1 / train | 137 | 56 | 280 | 67 |
| Week 2 / validation | None in this bucket | 0 | 0 | 0 |
| Week 3 / test-normal | 406 | 32 | 32 | 32 |
| Total | | 88 | 312 | 99 |

All 312 pairs decoded successfully and have distinct encoded image-pair hashes.
They are not therefore independent scenes or approved samples. Visual QC and label
assignment are still pending; matching hashes only detect exact encoded duplicates.

Of 224 extra training pairs explored, **11 pass the existing image-to-GT rule**.
All 11 are second-ranked pairs around **0% GT readings**; they also pass both the
100 ms and 250 ms camera-gap sensitivity checks. Recorded GT values bracketing
each pair agree at 0%. This supports further review but cannot prove the true fill
level was continuously unchanged between sensor readings. These additions improve
only 0% coverage; they do not add other fill levels within the bucket.

The remaining 213 extra training pairs exceed at least one image-to-GT limit.
Third-, fourth- and fifth-ranked pairs never pass both GT limits in this pilot.
Both selected camera topics in recording 137 have median inter-frame intervals of
about **2 seconds**, which limits how many distinct images fit near one GT event.

## Camera-gap sensitivity

Neither camera-pair cutoff has been activated. These are comparisons only:

| Camera-pair condition, plus existing GT limits | Train pairs including potential extras | Validation | Test-normal |
| --- | ---: | ---: | ---: |
| No additional pair cutoff | 67 | 0 | 32 |
| <=100 ms | 48 | 0 | 0 |
| <=250 ms | 48 | 0 | 0 |

Thus this bucket cannot currently support the planned complete train/val/test
comparison: it has no Week 2 GT events, and both proposed tight camera limits remove
its existing Week 3 test pairs. More suitable data, an explicitly revised protocol,
or a separate rematching investigation would be needed before evaluating a model
on this bucket alone.

## Split percentages and fill ranges

For the **88 original GT events** in this bucket:

| Split | Events | Percentage | Observed GT range |
| --- | ---: | ---: | --- |
| Train | 56 | 63.64% | 0–4% |
| Validation | 0 | 0% | No samples |
| Test-normal | 32 | 36.36% | 2–3% |

If all 11 extra training pairs are eventually approved, before any tighter camera
limit, the candidate counts would become 67 / 0 / 32: **67.68% / 0% / 32.32%**.
These are potential counts, not a released dataset. Fill ranges would remain the
same. Do not mistake the 280 exploratory training rows for approved samples.

## Artifacts

Under `extracted/low_fill_pilot_v1/`:

- `pilot_pairs.csv`: pandas table containing all 312 diagnostic rows.
- `additional_training_shortlist.csv`: the 11 extra pairs passing GT timing,
  decode, exact-pair uniqueness and recorded GT-bracket agreement checks. All are
  still pending manual visual/label review.
- `review.html`: paired narrow/wide images, timestamps and hold reasons.
- `counts_by_rank.csv`: timing and GT evidence by pair rank.
- `recording_camera_cadence.csv`: measured frame intervals for both sources.
- `summary.json`: reproducible counts, limitations and source-metadata checksum.

Open the images:

```bash
cd /Users/omkarkale/thesis_vlm
open extracted/low_fill_pilot_v1/review.html
```

Inspect the pandas table inside the container:

```python
import pandas as pd

df = pd.read_csv(
    '/workspace/extracted/low_fill_pilot_v1/pilot_pairs.csv',
    dtype={
        'gt_timestamp_ns': 'string',
        'narrow_timestamp_ns': 'string',
        'wide_timestamp_ns': 'string',
        'previous_gt_timestamp_ns': 'string',
        'next_gt_timestamp_ns': 'string',
        'bracket_start_ns': 'string',
        'bracket_end_ns': 'string',
    },
)
print(df[['proposed_split', 'gt_fill_level', 'gt_timestamp_utc', 'pair_rank',
          'narrow_timestamp_utc', 'wide_timestamp_utc', 'camera_pair_delta_ms',
          'passes_existing_gt_1s', 'gt_evidence']].to_string(index=False))
```

To create a new run, supply a new output directory (existing pilot runs are never
overwritten):

```bash
docker exec thesis-vlm-dev python3 '/workspace/script v2/pilot_low_fill_pairs.py' \
  --output /workspace/extracted/low_fill_pilot_v2
```

No model was trained or evaluated in this pilot. The existing dataset, split plan,
manual decisions and pending camera-cutoff choice have not been changed.
