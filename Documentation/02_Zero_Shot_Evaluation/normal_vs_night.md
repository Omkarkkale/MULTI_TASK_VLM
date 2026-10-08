# Normal vs Night Zero-Shot Comparison

## Overall MAE

| Model | Normal | Night |
|---|---:|---:|
| Qwen3.5-9B | 29.27 | 18.26 |
| DeepSeek V4.1 Flash | 20.01 | 25.14 |
| Qwen3.8-27B | 20.40 | 23.66 |
| GLM-5V-Turbo | 22.75 | 29.10 |

## Important Limitation

Overall normal-vs-night MAE does NOT represent a clean lighting experiment.

The target distributions differ.

Night data contains substantially more:

- 60-79%
- 80-100%

fill-level examples.

Qwen3.5 also tends to predict high values such as:

- 65%
- 75%
- 85%

Therefore the lower Qwen3.5 night MAE does not prove that Qwen3.5 performs better under night lighting.

Its prediction bias happens to align better with the night target distribution.

## Better Interpretation

Consider together:

- fill-level distribution
- bin-wise MAE
- prediction distribution
- prediction concentration

A stronger future lighting-domain experiment would ideally compare similar crusher states across lighting conditions.
