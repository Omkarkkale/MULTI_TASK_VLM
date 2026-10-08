# Dataset Status

## Current Target

Bjarne requested:

**>=10,000 meaningful normal-lighting samples**

before detailed training/fine-tuning.

## Latest Normal MCAP Scan

Date:

**2026-09-24**

Normal MCAPs scanned:

**44**

Total raw fill-level labels:

**6,773**

Of these:

- Previous v2 recordings: **1,542 raw labels**
- Newly added recordings: **5,231 raw labels**

## Important Finding

The complete current normal MCAP pool contains only:

**6,773 raw labels**

Therefore the current recordings alone cannot reach the >=10,000 clean-sample target.

Raw numerical deficit:

**3,227**

Because some labels will fail synchronization or QC, the practical target should be approximately:

**3,500-4,000 additional raw labels from additional recordings.**

## Current Raw Fill Distribution

| Range | Count |
|---|---:|
| 0-10% | 194 |
| 11-20% | 257 |
| 21-30% | 383 |
| 31-40% | 621 |
| 41-50% | 668 |
| 51-60% | 663 |
| 61-70% | 1090 |
| 71-80% | 1306 |
| 81-90% | 605 |
| 91-100% | 986 |

## Current Collection Priority

Highest priority:

- **0-10%**
- **11-20%**
- **21-30%**

Secondary priority:

- 31-60%
- 81-90%

Already strongly represented:

- 61-80%
- 91-100%

## Next Processing Step

Synchronize all candidate labels to:

- `front_narrow`
- `front_wide`

using:

- ROS `header.stamp`
- closest frame independently
- maximum absolute difference <=1.0 second

Then calculate synchronized distribution and perform visual QC.
