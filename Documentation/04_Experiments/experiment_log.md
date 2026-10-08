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
