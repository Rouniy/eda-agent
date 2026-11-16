# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 George Saliba <george.saliba@salitronic.com>
"""Every source file names its licence while preserving contributor notices."""
from __future__ import annotations

import subprocess
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SOURCE = (".py", ".pas", ".js", ".mjs", ".ts", ".ps1")


def _tracked():
    out = subprocess.run(["git", "ls-files"], cwd=_ROOT, capture_output=True,
                         text=True, check=True).stdout.splitlines()
    return [p for p in out if p.endswith(_SOURCE)
            and not p.startswith("reference/")]


def test_every_tracked_source_file_has_the_owner_and_licence():
    files = _tracked()
    assert files, "git ls-files returned nothing"
    missing = []
    for rel in files:
        path = _ROOT / rel
        if not path.exists():
            continue
        head = path.read_text(encoding="utf-8", errors="replace")[:800]
        if "SPDX-License-Identifier: Apache-2.0" not in head:
            missing.append(rel)
    assert not missing, (
        f"{len(missing)} source files lack an Apache-2.0 SPDX header: "
        f"{missing[:20]}")
