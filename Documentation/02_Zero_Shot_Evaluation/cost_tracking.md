# Zero-Shot Cost Tracking

## Completed Models

Normal four-model total:

**$2.8218**

Night four-model total:

**$7.2140**

Combined:

**$10.0359**

## Estimated Remaining Expensive Models

### Claude Opus

Normal 337:

approximately **$9.3**

Night 859:

approximately **$23.6**

Combined:

approximately **$32.9**

### Claude Fable

Normal:

approximately **$18.5**

Night:

approximately **$47.3**

Combined:

approximately **$65.8**

### GPT-6 Astra

Normal:

approximately **$21.5**

Night:

approximately **$54.8**

Combined:

approximately **$76.3**

These are estimates derived from pilot/probe usage and are not guaranteed final costs.

## Cost-Control Procedure

Before expensive runs:

1. run tiny compatibility test
2. limit completion tokens
3. use fixed deterministic prompt
4. log token counts
5. log per-request cost
6. estimate complete benchmark cost
7. only then run the full dataset
