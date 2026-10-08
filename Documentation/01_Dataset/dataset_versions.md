# Dataset Versions

## Dataset v3 — Candidate Preparation

The current 49 MCAPs have been audited directly: 7,638 raw labels and 7,576
synchronized candidates before full visual QC. Lighting suggestions and the
user-approved three-week chronological split are documented in
[the v3 audit report](v3_audit_report.md).

Candidate output: `extracted/crusher_dataset_v3_candidates/`.
Status: lighting/sample QC pending; splits are planned, not frozen.
The historical v2 results below describe the previous release.

## Normal Dataset v2

Path:

`/workspace/extracted/crusher_dataset_v2`

### Source Recordings

- 39
- 40
- 41
- 75
- 94
- 118
- 120
- 137

### Dataset Statistics

Raw fill labels:

**1,542**

Successfully synchronized:

**1,534**

Synchronization rejected:

**8**

Visual-QC rejected:

**15**

Final clean samples:

**1,519**

### Visual-QC Rejections

Recording 94:

- samples 0057-0061
- 5 samples rejected

Recording 118:

- samples 0104-0113
- 10 samples rejected

Reason:

Truck/vehicle obstruction of the relevant crusher view.

### Frozen Split

| Split | Recordings | Samples |
|---|---|---:|
| Train | 41, 75, 94, 120, 137 | 1,058 |
| Validation | 40 | 124 |
| Test | 39, 118 | 337 |
| Total | | 1,519 |

The split should be described as:

**Recording-chunk-level split to reduce temporal leakage**

The recordings may still come from the same broader operating session/day, so this should not automatically be described as independent-session generalization.

---

# Night Dataset v1

Path:

`/workspace/extracted/crusher_night_dataset_v1`

### Recordings

- 37
- 38
- 100
- 101
- 125

### Statistics

Raw fill labels:

**865**

Successfully synchronized:

**859**

Synchronization rejected:

**6**

Visual-QC rejected:

**0**

Final clean samples:

**859**

Total images:

**1,718**

Two images are used per sample.

---

# Planned Normal Dataset v3

Status:

**In progress**

Goal:

**>=10,000 meaningful normal-lighting samples**

The expanded dataset will be created only after:

1. MCAP inspection
2. fill-label analysis
3. camera synchronization
4. fill-distribution analysis
5. visual QC
6. near-duplicate review
7. recording-level split design
