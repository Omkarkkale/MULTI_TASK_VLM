# Zero-Shot Evaluation Protocol

## Fixed Prompt

Estimate the fill level of the industrial crusher shown in the two images. Use visual information from both images. The fill level is a percentage from 0 to 100, where 0 means completely empty and 100 means completely full. Return only the estimated percentage.

## Input

Every sample sends:

- front_narrow image
- front_wide image

## Generation

Temperature:

`0`

Maximum output tokens:

limited

Reasoning:

disabled where possible

## Valid Output

One numeric result satisfying:

`0 <= prediction <= 100`

## Metrics

For every model track:

- prediction
- ground truth
- absolute error
- MAE
- Median Absolute Error
- RMSE
- valid-output rate
- fill-bin MAE
- requested model
- resolved model
- raw output
- API success/failure
- prompt tokens
- completion tokens
- reasoning tokens
- total tokens
- API cost

## Additional Analysis

Prediction diversity was later added.

Track:

- number of unique ground-truth values
- number of unique predictions
- most common predictions
- prediction rounding
- prediction concentration
