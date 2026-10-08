# Project Timeline

## Phase 1 - Initial Crusher Dataset

The first normal-lighting crusher dataset was generated using selected MCAP recordings.

The pipeline used:

- `/processing/crusher/fill_level`
- `front_narrow`
- `front_wide`
- ROS `header.stamp`
- nearest-camera-frame synchronization
- maximum synchronization difference of 1.0 second

Final clean normal dataset:

**1,519 samples**

---

## Phase 2 - Normal Dataset Split

A recording-chunk-level split was created to reduce temporal leakage.

- Train: 1,058
- Validation: 124
- Test: 337

---

## Phase 3 - Night Dataset

Five night recordings were processed separately.

Final night dataset:

**859 samples**

The night dataset was intentionally kept outside normal training.

---

## Phase 4 - Zero-Shot Evaluation

Bjarne requested evaluation of several state-of-the-art model families before fine-tuning.

Four models were fully benchmarked:

- Qwen3.5-9B
- DeepSeek V4.1 Flash
- Qwen3.8-27B
- GLM-5V-Turbo

They were evaluated on:

- normal frozen test set
- night dataset

---

## Phase 5 - Result Analysis

Analysis included:

- MAE
- Median Absolute Error
- RMSE
- valid-output rate
- bin-wise errors
- prediction diversity
- prediction concentration
- API token usage
- API cost

A major finding was that zero-shot models frequently predicted only a small number of repeated percentage values.

---

## Phase 6 - Initial Fine-Tuning Planning

Qwen3.5-9B was selected as the primary fine-tuning candidate.

Candidate adaptation methods:

- LoRA
- QLoRA

---

## Phase 7 - Updated Decision from Bjarne

Bjarne advised:

- current dataset is too small
- increase the normal dataset to at least 10,000 samples
- discuss training script after dataset expansion
- do not use 420-vm as the main training GPU
- a separate GPU will be assigned specifically for the thesis

---

## Current Phase

Expand the normal-lighting dataset toward:

**>=10,000 meaningful samples**
