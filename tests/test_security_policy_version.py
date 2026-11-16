# SPDX-License-Identifier: Apache-2.0
"""Keep the fork's public security policy aligned with shipped metadata."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_security_policy_names_the_current_supported_version_line():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    major, minor, *_ = project["project"]["version"].split(".")
    series = f"{major}.{minor}.x"
    policy = (ROOT / "SECURITY.md").read_text(encoding="utf-8")

    assert re.search(rf"\|\s*{re.escape(series)}\s*\|\s*:white_check_mark:\s*\|", policy)
    assert f"current version {series}" in policy


def test_security_policy_covers_shipped_backends_and_no_removed_installer():
    policy = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
    for backend in ("Altium", "KiCad", "EasyEDA"):
        assert backend in policy
    assert "installer/" not in policy
