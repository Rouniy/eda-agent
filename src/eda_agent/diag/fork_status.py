# SPDX-License-Identifier: Apache-2.0
"""Report exact Git synchronization points for an eda-agent fork.

The report is read-only unless ``fetch`` is requested. A fork can have
independently ported features, so commit counts are Git history counts,
never a count of missing capabilities.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any


def _git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True,
        timeout=60, check=False,
    )
    if completed.returncode:
        raise RuntimeError((completed.stderr or completed.stdout).strip()
                           or f"git {' '.join(args)} failed")
    return completed.stdout.strip()


def fork_status(root: Path, *, remotes: tuple[str, ...] =
                ("origin", "upstream", "morembedded"),
                fetch: bool = False) -> dict[str, Any]:
    """Return HEAD, each remote tip, all merge bases and ahead/behind counts."""
    root = Path(root).resolve()
    head = _git(root, "rev-parse", "HEAD")
    branch = _git(root, "branch", "--show-current")
    configured = set(_git(root, "remote").splitlines())
    sources: dict[str, Any] = {}
    for remote in dict.fromkeys(remotes):
        if remote not in configured:
            sources[remote] = {"available": False, "reason": "remote not configured"}
            continue
        entry: dict[str, Any] = {"available": True, "refreshed": False}
        if fetch:
            try:
                _git(root, "fetch", "--no-tags", "--quiet", remote, "main")
                entry["refreshed"] = True
            except (RuntimeError, OSError, subprocess.TimeoutExpired) as exc:
                entry["fetch_error"] = str(exc)
        ref = f"{remote}/main"
        try:
            entry["tip"] = _git(root, "rev-parse", "--verify", ref)
            bases = _git(root, "merge-base", "--all", "HEAD", ref)
            entry["merge_bases"] = bases.splitlines()
            counts = _git(root, "rev-list", "--left-right", "--count",
                          f"HEAD...{ref}").split()
            entry["ahead"], entry["behind"] = map(int, counts)
            entry["tip_in_head"] = entry["tip"] == head or (
                entry["behind"] == 0)
        except (RuntimeError, OSError, ValueError, subprocess.TimeoutExpired) as exc:
            entry["available"] = False
            entry["reason"] = str(exc)
        sources[remote] = entry
    return {"root": str(root), "branch": branch, "head": head,
            "fetch_requested": fetch, "sources": sources}


def format_fork_status(report: dict[str, Any]) -> str:
    lines = [f"{report['branch'] or '(detached)'} {report['head']}",
             f"remote data: {'fetched now' if report['fetch_requested'] else 'local refs (use --fetch to refresh)'}"]
    for name, item in report["sources"].items():
        if not item["available"]:
            lines.append(f"{name}: unavailable ({item['reason']})")
            continue
        bases = ", ".join(item["merge_bases"]) or "none"
        lines.append(f"{name}: {item['tip']}; ahead {item['ahead']}, behind {item['behind']}; merge-base {bases}")
        if item.get("fetch_error"):
            lines.append(f"  fetch failed: {item['fetch_error']}; counts use cached refs")
    return "\n".join(lines)
