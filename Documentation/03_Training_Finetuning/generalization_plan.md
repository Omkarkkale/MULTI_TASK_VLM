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
