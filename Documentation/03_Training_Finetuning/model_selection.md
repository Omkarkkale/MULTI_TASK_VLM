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
