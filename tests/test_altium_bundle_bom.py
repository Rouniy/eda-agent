# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 George Saliba <george.saliba@salitronic.com>
"""The generated DelphiScript bundle must not contain a source-file BOM.

A byte-order mark at the head of one unit lands in the middle of the bundle,
where Altium reads it as a character of the code. The build therefore reads
every unit as ``utf-8-sig``. The build cannot be run on stub units any more
(it checks the generated rules region and the routines of the real sources),
so this reads how the build opens its sources and checks the real bundle.
"""

from __future__ import annotations

import ast
from pathlib import Path

ALTIUM = Path(__file__).resolve().parents[1] / "scripts" / "altium"
BOM = b"\xef\xbb\xbf"


def _bundle_loop_encodings() -> list[str]:
    """The encoding of every ``open(path, 'r', ...)`` in build.py."""
    tree = ast.parse((ALTIUM / "build.py").read_text(encoding="utf-8"))
    found = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and getattr(node.func, "id", "") == "open"
                and len(node.args) >= 2 and isinstance(node.args[1], ast.Constant)
                and node.args[1].value == "r"):
            for kw in node.keywords:
                if kw.arg == "encoding":
                    found.append(kw.value.value)
    return found


def test_build_reads_every_pascal_source_without_its_bom() -> None:
    encodings = _bundle_loop_encodings()
    assert encodings, "build.py no longer opens its sources with open(path, 'r')"
    assert set(encodings) == {"utf-8-sig"}, encodings


def test_the_bundle_holds_no_bom() -> None:
    bundle = ALTIUM / "Altium_MCP.pas"
    if bundle.exists():
        assert BOM not in bundle.read_bytes()
