# Dataset Processing Pipeline

## Current v3 preparation

The current raw-data audit, candidate exporter, lighting review and agreed
three-week chronology are documented in [the v3 audit report](v3_audit_report.md).
Use its commands for the expanded dataset. Legacy commands below describe the
earlier pipeline and may contain v2-specific paths or recording lists.

## Sample Structure

Each training/evaluation sample contains:

1. `front_narrow` image
2. `front_wide` image
3. crusher fill-level percentage
4. recording ID
5. sample ID
6. timestamps
7. synchronization metadata

## Ground Truth

Primary target topic:

`/processing/crusher/fill_level`

Example:

`63` means approximately `63%` crusher fill level.

`fill_volume_m3` is not used as the primary target.

## Synchronization

Synchronization uses ROS message:

`header.stamp`

For every fill-level label:

1. find the closest `front_narrow` image
2. find the closest `front_wide` image
3. match both independently
4. calculate absolute timestamp difference

Maximum allowed difference:

**1.0 second**

If either camera exceeds this threshold, reject the sample.

Do not use MCAP `log_time`.

## Quality-Control Rejection Rules

Reject samples if:

- truck blocks crusher view
- vehicle blocks relevant visual region
- narrow image is missing
- wide image is missing
- synchronization fails
- image is corrupted
- crusher cannot be meaningfully evaluated

## Dataset Expansion

Target:

**>=10,000 normal-lighting samples**

The objective is not simply to create 10,000 rows.

The dataset should also have:

- broad target coverage
- recording diversity
- reliable labels
- valid camera views
- limited unnecessary near-duplication
