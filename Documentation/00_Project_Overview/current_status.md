# Current Project Status

## Current Stage

The current priority is dataset expansion for the crusher fill-level VLM thesis.

Bjarne advised that the existing normal-lighting dataset is too small for the intended fine-tuning experiments.

The new target is:

**At least 10,000 meaningful normal-lighting samples**

## Existing Datasets

### Normal Dataset v2

- Clean samples: **1,519**
- Train: **1,058**
- Validation: **124**
- Test: **337**

### Night Dataset v1

- Clean samples: **859**
- Kept separate for cross-domain/generalization evaluation.

## Current MCAP Pool

- Total MCAPs: **49**
- Explicit night MCAPs: **5**
- Candidate normal MCAPs: **44**

## Current Work

The next stage is:

1. Scan all normal MCAPs.
2. Count `/processing/crusher/fill_level` labels.
3. Calculate fill-level ranges and distributions.
4. Identify underrepresented fill ranges.
5. Synchronize `front_narrow` and `front_wide`.
6. Perform visual QC.
7. Expand the dataset toward >=10,000 useful samples.

## Training Status

Training has **not started yet**.

Bjarne requested that the dataset first be expanded. After that, the training script and fine-tuning configuration will be discussed in detail.

## GPU Plan

The thesis will not use `420-vm` as the main training machine.

Bjarne will provide a **dedicated GPU for the thesis**.
