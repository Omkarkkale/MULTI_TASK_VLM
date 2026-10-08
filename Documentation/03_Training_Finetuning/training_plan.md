# Training Plan

## Current Status

Training has NOT started.

## Reason

Bjarne advised that the current dataset is too small.

Required first:

**>=10,000 meaningful normal-lighting samples**

After the expanded dataset is ready, the training script should be discussed in detail.

## Candidate Software Stack

- Qwen3.5-9B
- PyTorch
- CUDA
- Hugging Face Transformers
- PEFT
- Accelerate
- LoRA or QLoRA

## LoRA

LoRA adds trainable low-rank matrices while most of the base model remains frozen.

## QLoRA

QLoRA combines LoRA with a quantized base model.

Main benefit:

reduced GPU-memory requirement.

## CUDA

CUDA provides NVIDIA GPU acceleration.

CUDA is not an alternative to LoRA.

Possible stack:

Qwen3.5-9B  
+ LoRA/QLoRA  
+ PyTorch  
+ CUDA

## Parameters Still To Decide

- image resolution
- learning rate
- batch size
- gradient accumulation
- epochs
- LoRA rank
- LoRA alpha
- LoRA target modules
- quantization configuration
- gradient checkpointing
- scheduler
- warmup
- validation interval
- checkpoint interval
- checkpoint-selection rule
