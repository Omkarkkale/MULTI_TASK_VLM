# Bjarne - State-of-the-Art Zero-Shot Model Discussion

Before beginning fine-tuning, Bjarne requested a broad zero-shot evaluation using current strong model families.

Models/families discussed:

- Fable
- Opus
- GPT Astra
- Qwen3.8-2.4T-A95B
- Qwen3.8-27B
- Qwen3.5 around the 4B class
- DeepSeek
- Kimi K3
- GLM

The purpose was to establish strong zero-shot baselines before training a project-specific model.

## OpenRouter Compatibility Results

### Claude Fable

Requested:

`~anthropic/claude-fable-latest`

Resolved:

`anthropic/claude-fable-5.1`

### Claude Opus

Requested:

`~anthropic/claude-opus-latest`

Resolved:

`anthropic/claude-opus-5`

### GPT Astra

Requested:

`~openai/gpt-astra-latest`

Resolved:

`openai/gpt-6-astra`

### Qwen3.8-27B

`qwen/qwen3.8-27b`

Vision-capable and usable.

### Qwen3.8-2.4T-A95B

The tested endpoint did not provide a usable image endpoint during compatibility testing.

### Qwen3.5

Bjarne originally mentioned approximately the 4B scale.

The production benchmark used:

`qwen/qwen3.5-9b`

This discrepancy is intentionally documented.

### DeepSeek

`deepseek/deepseek-v4.1-flash`

### Kimi

`moonshotai/kimi-k3`

### GLM

`z-ai/glm-5v-turbo`
