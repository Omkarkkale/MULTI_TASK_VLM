from pathlib import Path
from textwrap import dedent

ROOT = Path("/workspace/Documentation")

docs = {

# ============================================================
# 00 PROJECT OVERVIEW
# ============================================================

"00_Project_Overview/README.md": """
# Crusher Fill-Level VLM Thesis

## Project Objective

The current thesis work investigates Vision-Language Models (VLMs) for estimating the fill level of an industrial crusher from camera images.

Each sample contains two camera views:

- `front_narrow`
- `front_wide`

The model should estimate an exact fill percentage between:

- `0%` = completely empty
- `100%` = completely full

Example expected output:

`63%`

The current task is therefore continuous numerical fill-level estimation rather than categorical classification.

## Ground Truth

Primary ground-truth topic:

`/processing/crusher/fill_level`

The labels are generated using Sensmore's LiDAR-based crusher processing.

Example:

A value of `25` means approximately `25%` full.

Bjarne advised that `fill_volume_m3` should not be treated as the primary target.

## Main Project Stages

1. Dataset preparation
2. Dataset synchronization
3. Dataset quality control
4. Zero-shot VLM evaluation
5. Zero-shot result analysis
6. Dataset expansion
7. Fine-tuning
8. In-domain evaluation
9. Night-domain/generalization evaluation

## Current Stage

The project is currently in the:

**Dataset Expansion Stage**

Bjarne requested at least:

**10,000 meaningful normal-lighting samples**

before moving into detailed training/fine-tuning.

## Documentation Purpose

This directory records:

- dataset versions
- MCAP inventory
- preprocessing rules
- QC decisions
- Bjarne discussions
- zero-shot model selection
- zero-shot results
- API costs
- model-selection reasoning
- fine-tuning plans
- GPU decisions
- experiment history
- important project decisions
""",

"00_Project_Overview/current_status.md": """
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
""",

"00_Project_Overview/project_timeline.md": """
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
""",

# ============================================================
# 01 DATASET
# ============================================================

"01_Dataset/dataset_versions.md": """
# Dataset Versions

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
""",

"01_Dataset/dataset_pipeline.md": """
# Dataset Processing Pipeline

## Sample Structure

Each training/evaluation sample contains:

1. `front_narrow` image
2. `front_wide` image
3. crusher fill-level percentage
4. recording ID
5. sample ID
6. timestamps
7. synchronization metadata

## Ground Truth

Primary target topic:

`/processing/crusher/fill_level`

Example:

`63` means approximately `63%` crusher fill level.

`fill_volume_m3` is not used as the primary target.

## Synchronization

Synchronization uses ROS message:

`header.stamp`

For every fill-level label:

1. find the closest `front_narrow` image
2. find the closest `front_wide` image
3. match both independently
4. calculate absolute timestamp difference

Maximum allowed difference:

**1.0 second**

If either camera exceeds this threshold, reject the sample.

Do not use MCAP `log_time`.

## Quality-Control Rejection Rules

Reject samples if:

- truck blocks crusher view
- vehicle blocks relevant visual region
- narrow image is missing
- wide image is missing
- synchronization fails
- image is corrupted
- crusher cannot be meaningfully evaluated

## Dataset Expansion

Target:

**>=10,000 normal-lighting samples**

The objective is not simply to create 10,000 rows.

The dataset should also have:

- broad target coverage
- recording diversity
- reliable labels
- valid camera views
- limited unnecessary near-duplication
""",

"01_Dataset/dataset_status.md": """
# Dataset Status

## Normal Dataset Target

Required before detailed training:

**>=10,000 meaningful normal-lighting samples**

## Current Existing Normal Dataset

Clean normal samples:

**1,519**

Relative to 10,000 target:

**15.19%**

This percentage will change after the newly added MCAPs are processed.

## Night Dataset

Clean night samples:

**859**

Night remains separate from the initial training dataset.

## Current MCAP Pool

Current `/workspace/data`:

- 49 MCAP files total
- 5 explicitly night
- 44 candidate normal recordings

## Current Work

For every candidate normal recording, determine:

- raw fill-label count
- min fill level
- max fill level
- mean fill level
- fill-level histogram
- camera availability
- synchronization success
- useful sample count
- QC rejection count

This information will be added to:

`mcap_dataset_inventory.csv`
""",

"01_Dataset/fill_level_distribution.md": """
# Fill-Level Distribution

## Purpose

The crusher target is continuous:

`0% - 100%`

The bins below are only used to understand dataset balance.

They are NOT model classes.

## Monitoring Bins

| Bin | Fill Range |
|---|---|
| 1 | 0-10% |
| 2 | 11-20% |
| 3 | 21-30% |
| 4 | 31-40% |
| 5 | 41-50% |
| 6 | 51-60% |
| 7 | 61-70% |
| 8 | 71-80% |
| 9 | 81-90% |
| 10 | 91-100% |

The VLM still predicts exact values such as:

`17%`

`63%`

`88%`

## 1,000-per-bin Reference

A perfectly balanced 10,000-sample dataset would contain approximately:

1,000 samples x 10 bins = 10,000 samples.

This is NOT a strict requirement.

The bins are used to identify severe imbalance.

Example:

If 60-80% already contains thousands of samples but 0-20% contains very few, future MCAP selection should prioritize low-fill recordings.

---

# Existing Normal v2

| Recording | Samples | Min | Max | Mean |
|---|---:|---:|---:|---:|
| 39 | 234 | 9 | 81 | 37.1 |
| 40 | 124 | 14 | 86 | 54.0 |
| 41 | 283 | 10 | 86 | 54.0 |
| 75 | 185 | 21 | 95 | 61.9 |
| 94 | 127 | 37 | 87 | 63.9 |
| 118 | 103 | 36 | 100 | 72.4 |
| 120 | 162 | 6 | 89 | 55.2 |
| 137 | 301 | 0 | 76 | 34.2 |
| ALL | 1,519 | 0 | 100 | 50.6 |

Median:

**54**

Standard deviation:

**23.2**

## Frozen Normal Test Distribution

| Fill Range | Samples | Share |
|---|---:|---:|
| 0-19 | 43 | 12.8% |
| 20-39 | 104 | 30.9% |
| 40-59 | 82 | 24.3% |
| 60-79 | 67 | 19.9% |
| 80-100 | 41 | 12.2% |

---

# Night Dataset v1

| Recording | Samples | Min | Max | Mean |
|---|---:|---:|---:|---:|
| 37 | 290 | 28 | 87 | 65.5 |
| 38 | 135 | 47 | 95 | 70.3 |
| 100 | 173 | 26 | 91 | 63.9 |
| 101 | 108 | 47 | 75 | 52.1 |
| 125 | 153 | 42 | 94 | 73.3 |
| ALL | 859 | 26 | 95 | 65.6 |

Median:

**70**

Night distribution:

| Fill Range | Samples | Share |
|---|---:|---:|
| 0-19 | 0 | 0.0% |
| 20-39 | 31 | 3.6% |
| 40-59 | 235 | 27.4% |
| 60-79 | 486 | 56.6% |
| 80-100 | 107 | 12.5% |

The night data is significantly shifted toward higher fill levels.
""",

"01_Dataset/qc_notes.md": """
# Dataset Quality-Control Notes

## Normal v2

Total visual-QC rejected:

**15**

Recording 94:

- samples 0057-0061
- 5 rejected

Recording 118:

- samples 0104-0113
- 10 rejected

Reason:

Vehicle/truck obstruction.

## Night v1

Visual-QC rejected:

**0**

## Future Expanded Dataset

Track every rejection using categories such as:

- synchronization failure
- missing narrow image
- missing wide image
- truck obstruction
- corrupted image
- bad visibility
- unusable crusher view
- near-duplicate concern
- other

Whenever possible retain:

- recording ID
- sample ID
- rejection reason
""",

# ============================================================
# 02 ZERO SHOT
# ============================================================

"02_Zero_Shot_Evaluation/bjarne_model_selection.md": """
# Bjarne - State-of-the-Art Zero-Shot Model Discussion

Before beginning fine-tuning, Bjarne requested a broad zero-shot evaluation using current strong model families.

Models/families discussed:

- Fable
- Opus
- GPT Astra
- Qwen3.8-2.4T-A95B
- Qwen3.8-27B
- Qwen3.5 around the 4B class
- DeepSeek
- Kimi K3
- GLM

The purpose was to establish strong zero-shot baselines before training a project-specific model.

## OpenRouter Compatibility Results

### Claude Fable

Requested:

`~anthropic/claude-fable-latest`

Resolved:

`anthropic/claude-fable-5.1`

### Claude Opus

Requested:

`~anthropic/claude-opus-latest`

Resolved:

`anthropic/claude-opus-5`

### GPT Astra

Requested:

`~openai/gpt-astra-latest`

Resolved:

`openai/gpt-6-astra`

### Qwen3.8-27B

`qwen/qwen3.8-27b`

Vision-capable and usable.

### Qwen3.8-2.4T-A95B

The tested endpoint did not provide a usable image endpoint during compatibility testing.

### Qwen3.5

Bjarne originally mentioned approximately the 4B scale.

The production benchmark used:

`qwen/qwen3.5-9b`

This discrepancy is intentionally documented.

### DeepSeek

`deepseek/deepseek-v4.1-flash`

### Kimi

`moonshotai/kimi-k3`

### GLM

`z-ai/glm-5v-turbo`
""",

"02_Zero_Shot_Evaluation/evaluation_protocol.md": """
# Zero-Shot Evaluation Protocol

## Fixed Prompt

Estimate the fill level of the industrial crusher shown in the two images. Use visual information from both images. The fill level is a percentage from 0 to 100, where 0 means completely empty and 100 means completely full. Return only the estimated percentage.

## Input

Every sample sends:

- front_narrow image
- front_wide image

## Generation

Temperature:

`0`

Maximum output tokens:

limited

Reasoning:

disabled where possible

## Valid Output

One numeric result satisfying:

`0 <= prediction <= 100`

## Metrics

For every model track:

- prediction
- ground truth
- absolute error
- MAE
- Median Absolute Error
- RMSE
- valid-output rate
- fill-bin MAE
- requested model
- resolved model
- raw output
- API success/failure
- prompt tokens
- completion tokens
- reasoning tokens
- total tokens
- API cost

## Additional Analysis

Prediction diversity was later added.

Track:

- number of unique ground-truth values
- number of unique predictions
- most common predictions
- prediction rounding
- prediction concentration
""",

"02_Zero_Shot_Evaluation/zero_shot_results.md": """
# Zero-Shot Benchmark Results

## Normal Frozen Test

Samples:

**337**

| Model | Valid | Valid Rate | MAE | Median AE | RMSE | Cost |
|---|---:|---:|---:|---:|---:|---:|
| Qwen3.5-9B | 337/337 | 100% | 29.27 | 28 | 35.17 | $0.1143 |
| DeepSeek V4.1 Flash | 298/337 | 88.43% | 20.01 | 17 | 25.15 | $0.1683 |
| Qwen3.8-27B | 335/337 | 99.41% | 20.40 | 18 | 25.29 | $0.3111 |
| GLM-5V-Turbo | 337/337 | 100% | 22.75 | 21 | 26.81 | $2.2281 |

Normal four-model total:

**$2.8218**

---

## Night Dataset

Samples:

**859**

| Model | Valid | Valid Rate | MAE | Median AE | RMSE | Cost |
|---|---:|---:|---:|---:|---:|---:|
| Qwen3.5-9B | 856/859 | 99.65% | 18.26 | 13 | 24.62 | $0.3002 |
| DeepSeek V4.1 Flash | 803/859 | 93.48% | 25.14 | 25 | 29.28 | $0.3966 |
| Qwen3.8-27B | 856/859 | 99.65% | 23.66 | 25 | 27.34 | $0.8379 |
| GLM-5V-Turbo | 859/859 | 100% | 29.10 | 31 | 31.81 | $5.6794 |

Night four-model total:

**$7.2140**

Combined:

**$10.0359**

## Real-World Interpretation

The tested models provide useful zero-shot baselines but currently show errors too large for precise automatic crusher fill estimation.

Several models also repeatedly predict only a few preferred percentage values.

Therefore zero-shot performance should be treated primarily as a baseline for later domain-specific fine-tuning.
""",

"02_Zero_Shot_Evaluation/prediction_concentration.md": """
# Prediction Concentration Analysis

## Why This Analysis Was Added

MAE alone does not show whether the model genuinely tracks the continuous target.

A model can achieve a moderate MAE by repeatedly predicting a few common values.

---

# Qwen3.5-9B Normal Test

Ground-truth unique values:

**91**

Prediction unique values:

**8**

| Prediction | Count |
|---|---:|
| 65% | 200 |
| 85% | 54 |
| 1% | 29 |
| 75% | 22 |
| 45% | 14 |
| 50% | 14 |
| 60% | 2 |
| 40% | 2 |

65%, 75%, and 85% together:

**81.9% of all predictions**

## Interpretation

The real crusher target showed 91 distinct values.

Qwen3.5 used only eight distinct numerical outputs.

This indicates strong zero-shot output concentration and poor continuous numerical calibration.

---

# DeepSeek Normal

Unique predictions:

**14**

Strong concentration around:

**35-45%**

45% alone:

**145 predictions**

---

# Qwen3.8-27B Normal

Unique predictions:

**9**

40% alone:

**225 predictions**

approximately:

**67.2% of valid predictions**

---

# GLM Normal

Unique predictions:

**10**

Predictions remain concentrated around rounded percentage values.

## Thesis Importance

Fine-tuning should not only reduce MAE.

It should ideally also:

- increase meaningful prediction diversity
- improve calibration
- improve sensitivity to different crusher states
""",

"02_Zero_Shot_Evaluation/normal_vs_night.md": """
# Normal vs Night Zero-Shot Comparison

## Overall MAE

| Model | Normal | Night |
|---|---:|---:|
| Qwen3.5-9B | 29.27 | 18.26 |
| DeepSeek V4.1 Flash | 20.01 | 25.14 |
| Qwen3.8-27B | 20.40 | 23.66 |
| GLM-5V-Turbo | 22.75 | 29.10 |

## Important Limitation

Overall normal-vs-night MAE does NOT represent a clean lighting experiment.

The target distributions differ.

Night data contains substantially more:

- 60-79%
- 80-100%

fill-level examples.

Qwen3.5 also tends to predict high values such as:

- 65%
- 75%
- 85%

Therefore the lower Qwen3.5 night MAE does not prove that Qwen3.5 performs better under night lighting.

Its prediction bias happens to align better with the night target distribution.

## Better Interpretation

Consider together:

- fill-level distribution
- bin-wise MAE
- prediction distribution
- prediction concentration

A stronger future lighting-domain experiment would ideally compare similar crusher states across lighting conditions.
""",

"02_Zero_Shot_Evaluation/cost_tracking.md": """
# Zero-Shot Cost Tracking

## Completed Models

Normal four-model total:

**$2.8218**

Night four-model total:

**$7.2140**

Combined:

**$10.0359**

## Estimated Remaining Expensive Models

### Claude Opus

Normal 337:

approximately **$9.3**

Night 859:

approximately **$23.6**

Combined:

approximately **$32.9**

### Claude Fable

Normal:

approximately **$18.5**

Night:

approximately **$47.3**

Combined:

approximately **$65.8**

### GPT-6 Astra

Normal:

approximately **$21.5**

Night:

approximately **$54.8**

Combined:

approximately **$76.3**

These are estimates derived from pilot/probe usage and are not guaranteed final costs.

## Cost-Control Procedure

Before expensive runs:

1. run tiny compatibility test
2. limit completion tokens
3. use fixed deterministic prompt
4. log token counts
5. log per-request cost
6. estimate complete benchmark cost
7. only then run the full dataset
""",

# ============================================================
# 03 TRAINING
# ============================================================

"03_Training_Finetuning/model_selection.md": """
# Fine-Tuning Model Selection

## Primary Candidate

**Qwen3.5-9B**

## Reasons

Qwen3.5-9B is:

- open-weight
- multimodal
- locally trainable
- suitable for LoRA/QLoRA
- much more practical than extremely large models
- already evaluated zero-shot on the thesis dataset

This enables an important controlled comparison:

**Qwen3.5 zero-shot**

versus

**Qwen3.5 after domain-specific fine-tuning**

## Important Clarification

The fine-tuning model was not selected purely according to lowest zero-shot MAE.

Other factors matter:

- model openness
- training feasibility
- GPU memory
- PEFT support
- experimental continuity
- reproducibility

## Qwen3.8-27B

Potentially usable, but substantially heavier.

Not currently the preferred first training model.

## API Models

Claude and GPT-family API models are useful benchmark/reference systems.

They are not currently the primary local training target.
""",

"03_Training_Finetuning/training_plan.md": """
# Training Plan

## Current Status

Training has NOT started.

## Reason

Bjarne advised that the current dataset is too small.

Required first:

**>=10,000 meaningful normal-lighting samples**

After the expanded dataset is ready, the training script should be discussed in detail.

## Candidate Software Stack

- Qwen3.5-9B
- PyTorch
- CUDA
- Hugging Face Transformers
- PEFT
- Accelerate
- LoRA or QLoRA

## LoRA

LoRA adds trainable low-rank matrices while most of the base model remains frozen.

## QLoRA

QLoRA combines LoRA with a quantized base model.

Main benefit:

reduced GPU-memory requirement.

## CUDA

CUDA provides NVIDIA GPU acceleration.

CUDA is not an alternative to LoRA.

Possible stack:

Qwen3.5-9B  
+ LoRA/QLoRA  
+ PyTorch  
+ CUDA

## Parameters Still To Decide

- image resolution
- learning rate
- batch size
- gradient accumulation
- epochs
- LoRA rank
- LoRA alpha
- LoRA target modules
- quantization configuration
- gradient checkpointing
- scheduler
- warmup
- validation interval
- checkpoint interval
- checkpoint-selection rule
""",

"03_Training_Finetuning/generalization_plan.md": """
# Generalization Experiment Plan

## Intended Main Experiment

Train using only:

**normal-lighting training data**

Use normal validation data for:

- validation
- checkpoint selection
- hyperparameter decisions

Then evaluate on:

## Normal Held-Out Test Set

Purpose:

Measure in-domain performance.

## Night Dataset

Purpose:

Measure cross-domain/generalization performance.

## Important Rule

The full 859-sample night set may be used for external evaluation as long as:

- no night sample is used during training
- no night sample is used for validation
- no night sample affects checkpoint selection

## Future Night Fine-Tuning

If night data is later used for adaptation:

first create recording-level partitions such as:

- night train
- night validation
- held-out night test

Do not train and test using frames from the same recording split.
""",

"03_Training_Finetuning/gpu_plan.md": """
# GPU Plan

## Original Plan

The RTX 5090 on:

`420-vm`

was initially considered for fine-tuning.

## Temporary Alternatives Discussed

While access was unavailable, the following alternatives were considered:

- Google Colab Pro
- Windows laptop with NVIDIA GPU
- Mac using MPS for small development tests
- CPU for pipeline validation

## Updated Decision from Bjarne

The final thesis training should NOT rely on:

`420-vm`

Bjarne will assign:

**a dedicated GPU machine specifically for the thesis**

## Current Strategy

Until that GPU is available:

1. expand dataset
2. analyze fill distribution
3. perform QC
4. maintain documentation

Once GPU is assigned:

1. inspect GPU model
2. inspect VRAM
3. verify CUDA
4. verify PyTorch GPU support
5. decide LoRA vs QLoRA
6. finalize training configuration
7. begin controlled fine-tuning experiments
""",

# ============================================================
# 04 EXPERIMENTS
# ============================================================

"04_Experiments/experiment_log.md": """
# Experiment Log

## Experiment 1 - Normal Dataset v2

Raw labels:

**1,542**

Synchronized:

**1,534**

Synchronization rejected:

**8**

Visual QC rejected:

**15**

Final:

**1,519**

---

## Experiment 2 - Night Dataset v1

Raw labels:

**865**

Synchronized:

**859**

Synchronization rejected:

**6**

Visual QC rejected:

**0**

Final:

**859**

---

## Experiment 3 - Normal Zero-Shot Benchmark

Dataset:

337 frozen normal test samples.

Models:

- Qwen3.5-9B
- DeepSeek V4.1 Flash
- Qwen3.8-27B
- GLM-5V-Turbo

Metrics:

- MAE
- Median AE
- RMSE
- valid-output rate
- fill-bin MAE
- token consumption
- API cost

---

## Experiment 4 - Night Zero-Shot Benchmark

Dataset:

859 night samples.

Same four models evaluated.

---

## Experiment 5 - Prediction Concentration

Added additional analysis because MAE did not fully explain model behavior.

Measured:

- unique GT values
- unique prediction values
- prediction frequency
- repeated output values
- rounding behavior

Strong prediction concentration was identified.

---

## Current Experiment - Expanded Normal Dataset

Goal:

**>=10,000 meaningful normal samples**

Current step:

Scan all available normal MCAPs and determine:

- fill-label count
- fill-level ranges
- target distribution
- useful recordings
""",

"04_Experiments/reproducibility_notes.md": """
# Reproducibility Notes

## Normal Dataset

Path:

`/workspace/extracted/crusher_dataset_v2`

Metadata:

`/workspace/extracted/crusher_dataset_v2/master_metadata.csv`

Splits:

`/workspace/extracted/crusher_dataset_v2/splits/train_metadata.csv`

`/workspace/extracted/crusher_dataset_v2/splits/val_metadata.csv`

`/workspace/extracted/crusher_dataset_v2/splits/test_metadata.csv`

## Night Dataset

Path:

`/workspace/extracted/crusher_night_dataset_v1`

Metadata:

`/workspace/extracted/crusher_night_dataset_v1/master_metadata.csv`

## Benchmark Scripts

Normal:

`/workspace/scripts/run_openrouter_benchmark.py`

Night:

`/workspace/scripts/run_openrouter_night_benchmark.py`

Normal vs Night:

`/workspace/scripts/create_normal_vs_night_comparison.py`

## OpenRouter API

API key environment variable:

`OPENROUTER_API_KEY`

Never store the actual key inside:

- Git
- documentation
- source code
- experiment logs
""",

# ============================================================
# 05 BJARNE / DECISIONS
# ============================================================

"05_Meetings_Decisions/bjarne_discussions.md": """
# Discussions with Bjarne

## VLM Thesis Direction

Bjarne proposed evaluating/training a VLM across several industrial fill-level tasks:

- shovel fill level
- pile fill level
- crusher/dumping-zone fill level

The broader research direction involves learning multiple related tasks.

The current implementation focuses first on:

**crusher fill-level estimation**

---

## Dataset Requirements

For the crusher task, Bjarne specified:

Use:

- `front_narrow`
- `front_wide`

Ground truth:

`/processing/crusher/fill_level`

A value such as:

`25`

means approximately:

`25% full`

The labels are generated through Sensmore's automatic LiDAR processing.

Bjarne advised not to strongly rely on:

`fill_volume_m3`

---

## Synchronization Requirements

Use:

ROS `header.stamp`

For every fill label:

- find nearest narrow camera frame
- find nearest wide camera frame
- match independently

Maximum allowed timestamp difference:

**1.0 second**

Do not use:

MCAP `log_time`

---

## Invalid Samples

Samples where a vehicle or truck blocks the relevant crusher view should be excluded.

---

## State-of-the-Art Zero-Shot Discussion

Before fine-tuning, Bjarne requested broad evaluation of current SOTA model families.

Models mentioned:

- Fable
- Opus
- GPT Astra
- Qwen3.8-2.4T-A95B
- Qwen3.8-27B
- Qwen3.5
- DeepSeek
- Kimi K3
- GLM

This became the basis for the zero-shot benchmark stage.

---

## OpenRouter Cost Discussion

API use must be controlled carefully.

The benchmark therefore records:

- requested model
- resolved model
- raw output
- prediction
- success/failure
- tokens
- cost

Pilot calls are used before full runs.

---

## Latest Dataset / Training Discussion

Bjarne stated that the current dataset of approximately 1,500 normal samples is too small for the intended training work.

New requirement:

**Increase the dataset to at least approximately 10,000 samples.**

After reaching sufficient dataset size:

- inspect dataset quality
- discuss training script in detail
- finalize fine-tuning configuration

---

## GPU Decision

The project will not rely on `420-vm` for final thesis training.

Bjarne will provide:

**a separate dedicated thesis GPU**
""",

"05_Meetings_Decisions/decision_register.md": """
# Project Decision Register

| Topic | Decision |
|---|---|
| Main task | Crusher fill-level estimation |
| Input | front_narrow + front_wide |
| Output | Exact percentage from 0-100 |
| Ground truth | /processing/crusher/fill_level |
| fill_volume_m3 | Not primary target |
| Timestamp source | ROS header.stamp |
| Camera matching | Closest frame independently |
| Max synchronization difference | 1.0 second |
| MCAP log_time | Do not use |
| Blocked crusher view | Reject sample |
| Normal dataset baseline | v2 - 1,519 samples |
| Night dataset baseline | v1 - 859 samples |
| Normal train set | 1,058 |
| Normal validation set | 124 |
| Normal test set | 337 |
| Split strategy | Recording/chunk-level |
| Zero-shot benchmark | Required before fine-tuning |
| Zero-shot models completed | Qwen3.5, DeepSeek, Qwen3.8, GLM |
| Extra zero-shot analysis | Prediction concentration |
| Fine-tuning candidate | Qwen3.5-9B |
| Candidate adaptation | LoRA / QLoRA |
| Dataset requirement | >=10,000 normal samples |
| Fill-level bins | Dataset analysis only |
| Exactly 1,000 per bin | Not required |
| Near duplicates | Avoid artificial dataset inflation |
| Night dataset | Keep separate for generalization |
| 420-vm | Not final training machine |
| Final training compute | Dedicated thesis GPU |
| Current priority | Dataset expansion |
""",
}


# ------------------------------------------------------------
# WRITE MARKDOWN DOCUMENTATION
# ------------------------------------------------------------

for relative_path, content in docs.items():

    path = ROOT / relative_path

    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    path.write_text(
        dedent(content).strip() + "\n",
        encoding="utf-8"
    )


# ------------------------------------------------------------
# MCAP INVENTORY CSV
# Do not destroy existing scan data if it is already populated.
# ------------------------------------------------------------

inventory = ROOT / "01_Dataset/mcap_dataset_inventory.csv"

if not inventory.exists() or inventory.stat().st_size == 0:

    inventory.write_text(
        "recording_id,"
        "filename,"
        "domain,"
        "scan_status,"
        "raw_fill_labels,"
        "valid_synced_samples,"
        "qc_rejected,"
        "final_usable_samples,"
        "min_fill,"
        "max_fill,"
        "mean_fill,"
        "bin_0_10,"
        "bin_11_20,"
        "bin_21_30,"
        "bin_31_40,"
        "bin_41_50,"
        "bin_51_60,"
        "bin_61_70,"
        "bin_71_80,"
        "bin_81_90,"
        "bin_91_100,"
        "notes\n",
        encoding="utf-8"
    )


print()
print("=" * 70)
print("Crusher VLM documentation populated successfully")
print("=" * 70)

for file in sorted(ROOT.rglob("*")):
    if file.is_file():
        lines = len(file.read_text(
            encoding="utf-8",
            errors="ignore"
        ).splitlines())

        print(f"{file.relative_to(ROOT)} : {lines} lines")

print("=" * 70)
