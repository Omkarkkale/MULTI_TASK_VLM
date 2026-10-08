# Normal MCAP Raw Fill-Level Scan

Date: **2026-09-24**

## Summary

- Normal MCAPs scanned: **44**
- Total raw fill labels: **6,773**
- Raw labels belonging to the eight previous v2 recordings: **1,542**
- Raw labels contributed by newly added recordings: **5,231**

## Important Dataset-Size Finding

The currently available normal MCAP pool cannot by itself produce 10,000 unique label-aligned samples.

Even before synchronization/QC, the current maximum is only **6,773 raw labels**.

Minimum numerical gap to 10,000: **3,227 labels**.

Because synchronization and QC will reject some samples, additional recordings should ideally provide approximately **3,500-4,000 more raw fill labels**.

## Raw Fill-Level Distribution

| Fill range | Labels | Share | ~1,000 reference gap |
|---|---:|---:|---:|
| 0-10% | 194 | 2.9% | 806 |
| 11-20% | 257 | 3.8% | 743 |
| 21-30% | 383 | 5.7% | 617 |
| 31-40% | 621 | 9.2% | 379 |
| 41-50% | 668 | 9.9% | 332 |
| 51-60% | 663 | 9.8% | 337 |
| 61-70% | 1,090 | 16.1% | Already >=1,000 |
| 71-80% | 1,306 | 19.3% | Already >=1,000 |
| 81-90% | 605 | 8.9% | 395 |
| 91-100% | 986 | 14.6% | 14 |

## Coverage Interpretation

Highest-priority ranges for additional recordings:

1. **0-10%**
2. **11-20%**
3. **21-30%**

Secondary priority:

- 31-40%
- 41-50%
- 51-60%
- 81-90%

Currently well represented:

- 61-70%
- 71-80%
- 91-100%

The ~1,000/bin value is a monitoring reference rather than a strict sampling quota.

## Useful New Recordings for Low-Fill Coverage

Examples worth prioritizing during synchronization/QC:

- Recording 138
- Recording 123
- Recording 406
- Recording 215
- Recording 377
- Recording 373
- Recording 42

These recordings contain useful coverage in the currently underrepresented lower fill ranges.

## Highly Concentrated Recordings

Some recordings have strong target concentration:

- 114: primarily 91-100%
- 145: primarily 91-100%
- 234: primarily 91-100%
- 281: primarily 71-80%
- 237: heavily concentrated around 41-50%

These recordings remain valid data, but should not be used to justify coverage of target ranges they do not represent.

## Next Step

Run camera synchronization using ROS `header.stamp` and the <=1.0 second rule, then calculate the **actual valid synchronized sample distribution**.

After synchronization, perform visual QC before freezing any expanded dataset version.
