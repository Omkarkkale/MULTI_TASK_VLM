#!/usr/bin/env python3
"""Guarded entry point for Qwen3.5 QLoRA fine-tuning.

This prevents a draft configuration from becoming an undocumented experiment.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    config = yaml.safe_load(args.config.read_text())
    if not config["experiment"].get("approved_for_run", False):
        raise SystemExit(
            "Blocked by design: obtain approval for dataset release, recording split, "
            "baselines, metrics, and QLoRA settings before fine-tuning."
        )
    raise SystemExit(
        "Protocol is approved. Next step: add the version-locked Qwen data collator, "
        "LoRA target modules, and smoke-test command in this script."
    )


if __name__ == "__main__":
    main()
