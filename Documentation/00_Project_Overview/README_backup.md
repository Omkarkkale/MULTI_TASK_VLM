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
