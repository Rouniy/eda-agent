# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 George Saliba <george.saliba@salitronic.com>
"""The generated DelphiScript bundle must not contain a source-file BOM."""

from __future__ import annotations

import ast
import shutil
import subprocess
import sys
from pathlib import Path


def test_build_strips_bom_from_each_pascal_source(tmp_path: Path) -> None:
    source = Path(__file__).resolve().parents[1] / "scripts" / "altium" / "build.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    files = next(
        ast.literal_eval(node.value)
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "FILES"
                for target in node.targets)
    )
    shutil.copy2(source, tmp_path / "build.py")
    for name in files:
        (tmp_path / name).write_bytes(b"\xef\xbb\xbf{ unit: " + name.encode() + b" }\n")

    subprocess.run([sys.executable, str(tmp_path / "build.py"), "--skip-lint"],
                   cwd=tmp_path, check=True, capture_output=True, text=True)
    bundle = (tmp_path / "Altium_MCP.pas").read_bytes()
    assert b"\xef\xbb\xbf" not in bundle
    for name in files:
        assert b"{ unit: " + name.encode() + b" }" in bundle
