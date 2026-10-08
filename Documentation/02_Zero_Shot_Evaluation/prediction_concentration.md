# Prediction Concentration Analysis

## Why This Analysis Was Added

MAE alone does not show whether the model genuinely tracks the continuous target.

A model can achieve a moderate MAE by repeatedly predicting a few common values.

---

# Qwen3.5-9B Normal Test

Ground-truth unique values:

**91**

Prediction unique values:

**8**

| Prediction | Count |
|---|---:|
| 65% | 200 |
| 85% | 54 |
| 1% | 29 |
| 75% | 22 |
| 45% | 14 |
| 50% | 14 |
| 60% | 2 |
| 40% | 2 |

65%, 75%, and 85% together:

**81.9% of all predictions**

## Interpretation

The real crusher target showed 91 distinct values.

Qwen3.5 used only eight distinct numerical outputs.

This indicates strong zero-shot output concentration and poor continuous numerical calibration.

---

# DeepSeek Normal

Unique predictions:

**14**

Strong concentration around:

**35-45%**

45% alone:

**145 predictions**

---

# Qwen3.8-27B Normal

Unique predictions:

**9**

40% alone:

**225 predictions**

approximately:

**67.2% of valid predictions**

---

# GLM Normal

Unique predictions:

**10**

Predictions remain concentrated around rounded percentage values.

## Thesis Importance

Fine-tuning should not only reduce MAE.

It should ideally also:

- increase meaningful prediction diversity
- improve calibration
- improve sensitivity to different crusher states
