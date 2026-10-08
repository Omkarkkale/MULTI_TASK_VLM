# Zero-Shot Benchmark Results

## Normal Frozen Test

Samples:

**337**

| Model | Valid | Valid Rate | MAE | Median AE | RMSE | Cost |
|---|---:|---:|---:|---:|---:|---:|
| Qwen3.5-9B | 337/337 | 100% | 29.27 | 28 | 35.17 | $0.1143 |
| DeepSeek V4.1 Flash | 298/337 | 88.43% | 20.01 | 17 | 25.15 | $0.1683 |
| Qwen3.8-27B | 335/337 | 99.41% | 20.40 | 18 | 25.29 | $0.3111 |
| GLM-5V-Turbo | 337/337 | 100% | 22.75 | 21 | 26.81 | $2.2281 |

Normal four-model total:

**$2.8218**

---

## Night Dataset

Samples:

**859**

| Model | Valid | Valid Rate | MAE | Median AE | RMSE | Cost |
|---|---:|---:|---:|---:|---:|---:|
| Qwen3.5-9B | 856/859 | 99.65% | 18.26 | 13 | 24.62 | $0.3002 |
| DeepSeek V4.1 Flash | 803/859 | 93.48% | 25.14 | 25 | 29.28 | $0.3966 |
| Qwen3.8-27B | 856/859 | 99.65% | 23.66 | 25 | 27.34 | $0.8379 |
| GLM-5V-Turbo | 859/859 | 100% | 29.10 | 31 | 31.81 | $5.6794 |

Night four-model total:

**$7.2140**

Combined:

**$10.0359**

## Real-World Interpretation

The tested models provide useful zero-shot baselines but currently show errors too large for precise automatic crusher fill estimation.

Several models also repeatedly predict only a few preferred percentage values.

Therefore zero-shot performance should be treated primarily as a baseline for later domain-specific fine-tuning.
