"""Helpers for saving a small, reproducible manifest for each future run."""

from __future__ import annotations

import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def git_commit(project_root: Path) -> str | None:
    """Return the current commit when Git is available; never abort a run for it."""

    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=project_root, text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def write_run_manifest(
    output_path: Path,
    *,
    experiment_id: str,
    command: list[str],
    config_path: Path,
    project_root: Path,
    extra: dict[str, Any] | None = None,
) -> None:
    """Write run identity, environment, and caller-supplied details as JSON."""

    payload: dict[str, Any] = {
        "experiment_id": experiment_id,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "command": command,
        "config_path": str(config_path.resolve()),
        "git_commit": git_commit(project_root),
        "python_version": sys.version,
        "platform": platform.platform(),
    }
    if extra:
        payload.update(extra)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    import json

    output_path.write_text(json.dumps(payload, indent=2) + "\n")
