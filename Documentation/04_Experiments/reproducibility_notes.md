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
