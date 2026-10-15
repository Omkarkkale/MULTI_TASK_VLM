# Crusher Fill — Pre-10k v1

## Status

**Exploratory only. Not a final thesis experiment.**

This folder records zero-shot work performed before the final clean 10k
dataset, recording-level split, prompt, and training protocol are frozen.

## Allowed purpose

- Check that model inference, image loading, numeric parsing, and result
  logging work end to end.
- Describe current-model behaviour on an explicitly named clean dataset
  release.

## Not allowed as a final claim

Do not label an MAE from this folder as the final zero-shot baseline if its
samples later influence prompt selection, model selection, or training design.
The official baseline is rerun in `../crusher_fill_10k_v1/` on the frozen test
split.

## Required record before a run

Fill in `zero_shot_config.yaml` with the exact clean metadata source, image
root, model, prompt, and output location.  Record the row count and source
recordings in `dataset_manifest.json`.

## Prepared command

First validate configuration and all image paths without loading Qwen:

```bash
python3 training/run_zero_shot.py \
  --config training/crusher_fill_pre10k_v1/zero_shot_config.yaml \
  --dry-run
```

The real runner remains blocked by `allow_run: false` in the configuration.
It supplies the established two-image fixed prompt in Qwen3.5's default
thinking mode. The complete output is retained, while evaluation parses only
the final response after any `</think>` block.
