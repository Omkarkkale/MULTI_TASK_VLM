# GPU Plan

## Original Plan

The RTX 5090 on:

`420-vm`

was initially considered for fine-tuning.

## Temporary Alternatives Discussed

While access was unavailable, the following alternatives were considered:

- Google Colab Pro
- Windows laptop with NVIDIA GPU
- Mac using MPS for small development tests
- CPU for pipeline validation

## Updated Decision from Bjarne

The final thesis training should NOT rely on:

`420-vm`

Bjarne will assign:

**a dedicated GPU machine specifically for the thesis**

## Current Strategy

Until that GPU is available:

1. expand dataset
2. analyze fill distribution
3. perform QC
4. maintain documentation

Once GPU is assigned:

1. inspect GPU model
2. inspect VRAM
3. verify CUDA
4. verify PyTorch GPU support
5. decide LoRA vs QLoRA
6. finalize training configuration
7. begin controlled fine-tuning experiments
