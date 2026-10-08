from pathlib import Path
import csv

DOC = Path("/workspace/Documentation")
DATASET = DOC / "01_Dataset"

# ============================================================
# MCAP SCAN RESULTS
# ============================================================

rows = [
("0",13,71,71,71.0,[0,0,0,0,0,0,0,13,0,0]),
("114",287,73,100,91.7,[0,0,0,0,0,0,0,89,0,198]),
("118",115,36,100,72.2,[0,0,0,6,11,17,20,20,13,28]),
("120",162,6,89,55.2,[5,0,27,0,9,59,33,5,24,0]),
("121",68,63,100,89.9,[0,0,0,0,0,0,2,13,18,35]),
("123",152,6,100,27.4,[24,44,28,27,22,1,0,0,0,6]),
("124",99,32,93,72.2,[0,0,0,8,0,4,38,19,27,3]),
("137",303,0,76,34.5,[69,51,12,52,35,32,7,45,0,0]),
("138",293,7,67,31.5,[23,45,68,106,23,10,18,0,0,0]),
("142",39,59,94,74.6,[0,0,0,0,0,4,5,20,9,1]),
("145",298,37,97,87.9,[0,0,0,5,10,9,28,17,10,219]),
("208",104,32,96,67.8,[0,0,0,6,7,15,27,31,12,6]),
("215",103,10,97,55.7,[22,3,5,2,1,13,14,18,16,9]),
("217",272,28,85,61.9,[0,0,7,26,38,57,52,43,49,0]),
("221",174,38,100,54.7,[0,0,0,86,12,13,16,18,21,8]),
("234",187,70,100,98.2,[0,0,0,0,0,0,1,7,8,171]),
("237",227,18,82,48.7,[0,4,14,9,169,6,10,12,3,0]),
("245",145,54,97,65.1,[0,0,0,0,0,86,11,27,14,7]),
("265",34,67,98,89.8,[0,0,0,0,0,0,1,2,14,17]),
("281",273,20,89,69.9,[0,1,17,15,17,16,9,191,7,0]),
("309",54,63,94,80.5,[0,0,0,0,0,0,10,15,20,9]),
("312",122,55,87,73.8,[0,0,0,0,0,8,32,57,25,0]),
("373",267,13,85,59.5,[0,15,25,18,13,22,34,131,9,0]),
("377",242,7,95,66.6,[9,27,19,25,9,6,6,6,7,128]),
("384",129,52,100,83.1,[0,0,0,0,0,15,11,28,21,54]),
("39",234,9,81,37.1,[9,38,49,49,35,24,16,13,1,0]),
("40",125,14,86,53.8,[0,8,11,14,22,22,13,21,14,0]),
("404",78,44,94,70.4,[0,0,0,0,5,5,47,6,0,15]),
("406",108,2,99,46.6,[32,0,6,0,26,1,7,11,16,9]),
("41",284,10,86,54.1,[1,16,39,27,30,8,146,9,8,0]),
("412",59,65,98,78.3,[0,0,0,0,0,0,26,7,12,14]),
("42",297,18,70,53.3,[0,5,32,46,45,29,140,0,0,0]),
("43",132,33,88,68.9,[0,0,0,8,2,15,39,47,21,0]),
("446",61,57,97,79.6,[0,0,0,0,0,3,15,19,4,20]),
("46",129,26,87,59.0,[0,0,6,19,19,21,24,24,16,0]),
("47",77,52,91,74.0,[0,0,0,0,0,7,23,24,21,2]),
("479",114,54,95,80.0,[0,0,0,0,0,4,10,41,48,11]),
("49",184,22,85,51.9,[0,0,15,44,39,24,30,22,10,0]),
("51",38,38,86,66.4,[0,0,0,2,7,2,8,13,6,0]),
("75",187,21,95,61.5,[0,0,3,12,26,45,45,40,10,6]),
("76",121,58,94,78.4,[0,0,0,0,0,2,15,56,44,4]),
("94",132,37,87,64.5,[0,0,0,6,22,20,28,44,12,0]),
("95",147,37,88,66.0,[0,0,0,3,12,28,48,39,17,0]),
("99",104,49,93,73.8,[0,0,0,0,2,10,25,43,18,6]),
]

existing_v2 = {"39","40","41","75","94","118","120","137"}

# ============================================================
# WRITE INVENTORY CSV
# ============================================================

inventory = DATASET / "mcap_dataset_inventory.csv"

header = [
    "recording_id",
    "domain",
    "previous_dataset",
    "scan_status",
    "raw_fill_labels",
    "min_fill",
    "max_fill",
    "mean_fill",
    "bin_0_10",
    "bin_11_20",
    "bin_21_30",
    "bin_31_40",
    "bin_41_50",
    "bin_51_60",
    "bin_61_70",
    "bin_71_80",
    "bin_81_90",
    "bin_91_100",
    "valid_synced_samples",
    "qc_rejected",
    "final_usable_samples",
    "notes",
]

with inventory.open("w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(header)

    for rec, count, minimum, maximum, mean, bins in rows:

        previous = "normal_v2" if rec in existing_v2 else ""

        writer.writerow([
            rec,
            "normal",
            previous,
            "raw_scan_complete",
            count,
            minimum,
            maximum,
            mean,
            *bins,
            "",
            "",
            "",
            "",
        ])

# ============================================================
# TOTALS
# ============================================================

total = sum(row[1] for row in rows)

bin_totals = [
    sum(row[5][i] for row in rows)
    for i in range(10)
]

old_raw = sum(
    row[1]
    for row in rows
    if row[0] in existing_v2
)

new_raw = total - old_raw

labels = [
    "0-10%",
    "11-20%",
    "21-30%",
    "31-40%",
    "41-50%",
    "51-60%",
    "61-70%",
    "71-80%",
    "81-90%",
    "91-100%",
]

# ============================================================
# WRITE SCAN REPORT
# ============================================================

report = DATASET / "normal_mcap_scan_2026-09-24.md"

lines = [
"# Normal MCAP Raw Fill-Level Scan",
"",
"Date: **2026-09-24**",
"",
"## Summary",
"",
f"- Normal MCAPs scanned: **{len(rows)}**",
f"- Total raw fill labels: **{total:,}**",
f"- Raw labels belonging to the eight previous v2 recordings: **{old_raw:,}**",
f"- Raw labels contributed by newly added recordings: **{new_raw:,}**",
"",
"## Important Dataset-Size Finding",
"",
"The currently available normal MCAP pool cannot by itself produce 10,000 unique label-aligned samples.",
"",
f"Even before synchronization/QC, the current maximum is only **{total:,} raw labels**.",
"",
f"Minimum numerical gap to 10,000: **{10000-total:,} labels**.",
"",
"Because synchronization and QC will reject some samples, additional recordings should ideally provide approximately **3,500-4,000 more raw fill labels**.",
"",
"## Raw Fill-Level Distribution",
"",
"| Fill range | Labels | Share | ~1,000 reference gap |",
"|---|---:|---:|---:|",
]

for label, value in zip(labels, bin_totals):
    share = value / total * 100
    gap = max(0, 1000 - value)

    if gap:
        gap_text = str(gap)
    else:
        gap_text = "Already >=1,000"

    lines.append(
        f"| {label} | {value:,} | {share:.1f}% | {gap_text} |"
    )

lines += [
"",
"## Coverage Interpretation",
"",
"Highest-priority ranges for additional recordings:",
"",
"1. **0-10%**",
"2. **11-20%**",
"3. **21-30%**",
"",
"Secondary priority:",
"",
"- 31-40%",
"- 41-50%",
"- 51-60%",
"- 81-90%",
"",
"Currently well represented:",
"",
"- 61-70%",
"- 71-80%",
"- 91-100%",
"",
"The ~1,000/bin value is a monitoring reference rather than a strict sampling quota.",
"",
"## Useful New Recordings for Low-Fill Coverage",
"",
"Examples worth prioritizing during synchronization/QC:",
"",
"- Recording 138",
"- Recording 123",
"- Recording 406",
"- Recording 215",
"- Recording 377",
"- Recording 373",
"- Recording 42",
"",
"These recordings contain useful coverage in the currently underrepresented lower fill ranges.",
"",
"## Highly Concentrated Recordings",
"",
"Some recordings have strong target concentration:",
"",
"- 114: primarily 91-100%",
"- 145: primarily 91-100%",
"- 234: primarily 91-100%",
"- 281: primarily 71-80%",
"- 237: heavily concentrated around 41-50%",
"",
"These recordings remain valid data, but should not be used to justify coverage of target ranges they do not represent.",
"",
"## Next Step",
"",
"Run camera synchronization using ROS `header.stamp` and the <=1.0 second rule, then calculate the **actual valid synchronized sample distribution**.",
"",
"After synchronization, perform visual QC before freezing any expanded dataset version.",
]

report.write_text(
    "\n".join(lines) + "\n",
    encoding="utf-8"
)

# ============================================================
# UPDATE DATASET STATUS
# ============================================================

status = DATASET / "dataset_status.md"

status.write_text(f"""# Dataset Status

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

**{total:,}**

Of these:

- Previous v2 recordings: **{old_raw:,} raw labels**
- Newly added recordings: **{new_raw:,} raw labels**

## Important Finding

The complete current normal MCAP pool contains only:

**{total:,} raw labels**

Therefore the current recordings alone cannot reach the >=10,000 clean-sample target.

Raw numerical deficit:

**{10000-total:,}**

Because some labels will fail synchronization or QC, the practical target should be approximately:

**3,500-4,000 additional raw labels from additional recordings.**

## Current Raw Fill Distribution

| Range | Count |
|---|---:|
| 0-10% | {bin_totals[0]} |
| 11-20% | {bin_totals[1]} |
| 21-30% | {bin_totals[2]} |
| 31-40% | {bin_totals[3]} |
| 41-50% | {bin_totals[4]} |
| 51-60% | {bin_totals[5]} |
| 61-70% | {bin_totals[6]} |
| 71-80% | {bin_totals[7]} |
| 81-90% | {bin_totals[8]} |
| 91-100% | {bin_totals[9]} |

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
""", encoding="utf-8")

print("Documentation updated.")
print()
print(f"Normal MCAPs: {len(rows)}")
print(f"Total raw labels: {total}")
print(f"Existing-v2 raw labels: {old_raw}")
print(f"New raw labels: {new_raw}")
print(f"Raw deficit to 10,000: {10000-total}")
print()
print("Bin totals:")
for label, value in zip(labels, bin_totals):
    print(f"{label:>8}: {value}")
