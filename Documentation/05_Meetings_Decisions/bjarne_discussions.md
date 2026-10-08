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
