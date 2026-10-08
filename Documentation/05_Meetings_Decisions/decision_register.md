# Project Decision Register

| Topic | Decision |
|---|---|
| Main task | Crusher fill-level estimation |
| Input | front_narrow + front_wide |
| Output | Exact percentage from 0-100 |
| Ground truth | /processing/crusher/fill_level |
| fill_volume_m3 | Not primary target |
| Timestamp source | ROS header.stamp |
| Camera matching | Closest frame independently |
| Max synchronization difference | 1.0 second |
| MCAP log_time | Do not use |
| Blocked crusher view | Reject sample |
| Normal dataset baseline | v2 - 1,519 samples |
| Night dataset baseline | v1 - 859 samples |
| Normal train set | 1,058 |
| Normal validation set | 124 |
| Normal test set | 337 |
| Split strategy | Recording/chunk-level |
| Zero-shot benchmark | Required before fine-tuning |
| Zero-shot models completed | Qwen3.5, DeepSeek, Qwen3.8, GLM |
| Extra zero-shot analysis | Prediction concentration |
| Fine-tuning candidate | Qwen3.5-9B |
| Candidate adaptation | LoRA / QLoRA |
| Dataset requirement | >=10,000 normal samples |
| Fill-level bins | Dataset analysis only |
| Exactly 1,000 per bin | Not required |
| Near duplicates | Avoid artificial dataset inflation |
| Night dataset | Keep separate for generalization |
| 420-vm | Not final training machine |
| Final training compute | Dedicated thesis GPU |
| Current priority | Dataset expansion |
