# Crusher Fill-Level Training Draft

This directory is a **discussion draft**, not a finalized experiment.  It is
intended to make the training decisions visible and reproducible before any
final model run.

## What is intentionally not decided yet

- the official clean dataset release and its checksum/count;
- the recording-level train/validation/test assignment;
- the final zero-shot prompt and invalid-answer rule;
- whether the input is two camera views, one view, or both variants;
- the final QLoRA hyperparameters and number of final random seeds.

`configs/qwen35_qlora_draft.yaml` contains these items.  Values marked
`CONFIRM_WITH_BJARNE` must be approved and changed before a final run.

## Planned experiment

All methods use the same frozen, recording-level test split:

1. `run_mean_baseline.py`: predicts the mean fill level from the training set.
2. `run_zero_shot.py`: evaluates the base Qwen model without crusher labels.
3. `train_qlora.py`: fine-tunes Qwen with QLoRA on training recordings only.
4. `evaluate.py`: calculates MAE and writes transparent per-sample results.

Supporting pre-meeting components:

- `crusher_dataset.py`: model-independent loader for the two synchronized
  camera images and numeric fill-level target;
- `preflight_dataset.py`: read-only schema/image-path/count check that can
  write a dataset manifest only when explicitly requested;
- `experiment_logging.py`: helper used by future runners to record command,
  Git commit, package/environment details, and configuration identity.

The zero-shot and QLoRA launchers are guarded by
`experiment.approved_for_run: false`.  This prevents accidentally treating
the draft as the final thesis protocol.

## Intended workflow after discussion

1. Copy `splits/recording_assignments_TEMPLATE.csv` to a new, dated CSV and
   assign every recording exactly once.
2. Set the official dataset root and metadata CSV in the configuration.
3. Run `python training/make_splits.py --config ... --assignments ...`.
4. Run the mean baseline and evaluation first.
5. Validate the zero-shot prompt on validation recordings only.
6. After the method is frozen, set `approved_for_run: true` and run the
   zero-shot and QLoRA experiments.

## Safety rules encoded by this draft

- A recording cannot appear in more than one split.
- Every metadata row must be assigned to a split.
- The test split is never used to choose a prompt or training setting.
- Generated predictions retain sample ID, recording ID, ground truth, raw
  output, parsed prediction, and validity status.

## Current scope

The scripts support the established clean metadata columns:
`recording_id`, `sample`, `front_narrow`, `front_wide`, and `fill_level`.
Paths in the CSV are interpreted relative to `dataset.root`.

## Preflight example

This performs a read-only check when `--manifest-output` is omitted:

```bash
python training/preflight_dataset.py \
  --metadata-csv /path/to/master_metadata_clean.csv \
  --image-root /path/to/dataset_root
```

For a logical combined release with a `source_dataset` column, supply its
source-root map as well:

```bash
python training/preflight_dataset.py \
  --metadata-csv extracted/crusher_dataset_v4/master_metadata_clean.csv \
  --image-root extracted/crusher_dataset_v4 \
  --source-roots-json extracted/crusher_dataset_v4/source_roots.json
```

No model weights, dataset files, adapters, predictions, or checkpoints belong
in Git.  They should remain under ignored data/result directories.
