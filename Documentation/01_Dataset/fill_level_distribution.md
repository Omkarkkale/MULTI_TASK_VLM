# Fill-Level Distribution

## Purpose

The crusher target is continuous:

`0% - 100%`

The bins below are only used to understand dataset balance.

They are NOT model classes.

## Monitoring Bins

| Bin | Fill Range |
|---|---|
| 1 | 0-10% |
| 2 | 11-20% |
| 3 | 21-30% |
| 4 | 31-40% |
| 5 | 41-50% |
| 6 | 51-60% |
| 7 | 61-70% |
| 8 | 71-80% |
| 9 | 81-90% |
| 10 | 91-100% |

The VLM still predicts exact values such as:

`17%`

`63%`

`88%`

## 1,000-per-bin Reference

A perfectly balanced 10,000-sample dataset would contain approximately:

1,000 samples x 10 bins = 10,000 samples.

This is NOT a strict requirement.

The bins are used to identify severe imbalance.

Example:

If 60-80% already contains thousands of samples but 0-20% contains very few, future MCAP selection should prioritize low-fill recordings.

---

# Existing Normal v2

| Recording | Samples | Min | Max | Mean |
|---|---:|---:|---:|---:|
| 39 | 234 | 9 | 81 | 37.1 |
| 40 | 124 | 14 | 86 | 54.0 |
| 41 | 283 | 10 | 86 | 54.0 |
| 75 | 185 | 21 | 95 | 61.9 |
| 94 | 127 | 37 | 87 | 63.9 |
| 118 | 103 | 36 | 100 | 72.4 |
| 120 | 162 | 6 | 89 | 55.2 |
| 137 | 301 | 0 | 76 | 34.2 |
| ALL | 1,519 | 0 | 100 | 50.6 |

Median:

**54**

Standard deviation:

**23.2**

## Frozen Normal Test Distribution

| Fill Range | Samples | Share |
|---|---:|---:|
| 0-19 | 43 | 12.8% |
| 20-39 | 104 | 30.9% |
| 40-59 | 82 | 24.3% |
| 60-79 | 67 | 19.9% |
| 80-100 | 41 | 12.2% |

---

# Night Dataset v1

| Recording | Samples | Min | Max | Mean |
|---|---:|---:|---:|---:|
| 37 | 290 | 28 | 87 | 65.5 |
| 38 | 135 | 47 | 95 | 70.3 |
| 100 | 173 | 26 | 91 | 63.9 |
| 101 | 108 | 47 | 75 | 52.1 |
| 125 | 153 | 42 | 94 | 73.3 |
| ALL | 859 | 26 | 95 | 65.6 |

Median:

**70**

Night distribution:

| Fill Range | Samples | Share |
|---|---:|---:|
| 0-19 | 0 | 0.0% |
| 20-39 | 31 | 3.6% |
| 40-59 | 235 | 27.4% |
| 60-79 | 486 | 56.6% |
| 80-100 | 107 | 12.5% |

The night data is significantly shifted toward higher fill levels.
