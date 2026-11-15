"""ORACLE package."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

__version__ = "4.0.0"
__schema_version__ = "oracle-delivery.v1"


def _detect_git_hash() -> str:
    env_hash = str(os.environ.get("ORACLE_BUILD_GIT", "") or "").strip()
    if env_hash:
        return env_hash
    try:
        root = Path(__file__).resolve().parents[1]
        # -c safe.directory=* avoids git's "dubious ownership" refusal, which
        # fires whenever the process UID doesn't own the working tree — the
        # common case in containers, VMs, and synced/mounted dev folders
        # (root running against a host-owned checkout, etc). Without this,
        # git exits non-zero and the build badge silently shows "unknown"
        # even though a perfectly good git history is sitting right there.
        proc = subprocess.run(
            ["git", "-c", "safe.directory=*", "rev-parse", "--short", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=1.5,
            check=True,
        )
        short_hash = proc.stdout.strip()
        if short_hash:
            return short_hash
    except Exception:
        pass
    # Fall back to a hash baked in at package/Docker build time, for
    # installs (pip, Docker images) that don't ship a .git directory at all.
    try:
        baked = (Path(__file__).resolve().parent / "_build_info.txt").read_text().strip()
        if baked:
            return baked
    except Exception:
        pass
    return "unknown"


__build_git__ = _detect_git_hash()


def get_build_identity() -> dict[str, Any]:
    return {
        "semantic_version": __version__,
        "git_hash": __build_git__,
        "schema_version": __schema_version__,
    }


__all__ = ["__version__", "__schema_version__", "__build_git__", "get_build_identity"]
