# SPDX-License-Identifier: Apache-2.0
"""Discover bridge capabilities from the installed DelphiScript bundle."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


_HANDLER_FILE = {
    "application": "Application.pas", "project": "Project.pas",
    "library": "Library.pas", "generic": "Generic.pas",
    "pcb": "PCB.pas", "audit": "Audit.pas",
}
_ACTION_RE = re.compile(r"(?:If|Else\s+If)\s+Action\s*=\s*'([^']+)'", re.I)
_CASE_ACTION_RE = re.compile(r"^\s*'([^']+)'\s*:", re.M)


def inspect_script_capabilities(script_dir: Path) -> dict[str, Any]:
    """Return command actions actually handled by the on-disk scripts."""
    categories: dict[str, list[str]] = {}
    missing = []
    for category, filename in _HANDLER_FILE.items():
        path = script_dir / filename
        if not path.exists():
            missing.append(filename)
            categories[category] = []
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        categories[category] = sorted(set(
            _ACTION_RE.findall(text) + _CASE_ACTION_RE.findall(text)
        ))
    return {
        "script_dir": str(script_dir),
        "categories": categories,
        "command_count": sum(len(actions) for actions in categories.values()),
        "missing_files": missing,
        "complete_bundle": not missing,
    }
