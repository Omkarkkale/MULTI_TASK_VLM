# Crusher Fill — 10k v1

## Status

**Planned official experiment. Do not run until the protocol is agreed with
Bjarne and the dataset is frozen.**

This folder will hold the reproducible record for the first 10k-sample
crusher-fill experiment.  The reusable code remains in the parent `training/`
directory; this folder contains only this experiment's data identity,
recording split, configurations, and summaries.

## Required methods

1. Mean-value baseline.
2. Qwen3.5-9B zero-shot baseline.
3. Qwen3.5-9B + QLoRA fine-tuning.

Methods 2 and 3 must use the same frozen test recordings. QLoRA uses only the
train recordings for updates and validation recordings for model decisions.

## Before an official run

1. Complete `dataset_manifest.json` from the approved clean dataset release.
2. Copy recording IDs into `recording_split.csv`, assigning each exactly once.
3. Discuss and complete `zero_shot_config.yaml` and `qlora_config.yaml`.
4. Set the final experiment status in both configurations only after approval.
