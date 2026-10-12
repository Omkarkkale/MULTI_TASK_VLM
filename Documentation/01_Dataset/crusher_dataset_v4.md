# Crusher Dataset v4

## Purpose

`crusher_dataset_v4` is a logical combined clean release for the pre-10k
exploratory stage. It combines clean metadata from:

- `extracted/crusher_dataset_v3/`
- `extracted/new_batches/2026_09_28/`

No image data is copied or modified. The combined CSV adds `source_dataset`,
and `source_roots.json` maps that value to the immutable image-root folder.

## Provenance

The generated `dataset_manifest.json` records row counts, recording IDs, and
SHA256 hashes of each source clean metadata CSV. Rebuild only with:

```bash
python3 scripts/create_combined_clean_dataset_v4.py
```

This release is the intended input pool for `training/crusher_fill_pre10k_v1`.
It is not automatically the frozen final 10k thesis dataset or test split.
