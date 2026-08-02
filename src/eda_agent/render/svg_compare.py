# SPDX-License-Identifier: Apache-2.0
"""Offline visual comparison artifacts for structured EDA SVG exports."""

from __future__ import annotations

import base64
import hashlib
import re
from pathlib import Path
from typing import Any


_VIEWBOX = re.compile(r'viewBox=["\']([^"\']+)["\']', re.I)
_DATA_OBJECT = re.compile(r'<g\b[^>]*\bdata-(?:designator|net|pin|layer)=', re.I)


def _dimensions(svg: str) -> tuple[float, float]:
    match = _VIEWBOX.search(svg)
    if not match:
        return 1000.0, 700.0
    values = [float(v) for v in match.group(1).replace(",", " ").split()]
    if len(values) != 4 or values[2] <= 0 or values[3] <= 0:
        return 1000.0, 700.0
    return values[2], values[3]


def compare_svg_files(before: Path, after: Path, output: Path) -> dict[str, Any]:
    """Write a self-contained side-by-side before/after SVG."""
    before_text = before.read_text(encoding="utf-8")
    after_text = after.read_text(encoding="utf-8")
    bw, bh = _dimensions(before_text)
    aw, ah = _dimensions(after_text)
    panel_w, panel_h = max(bw, aw), max(bh, ah)
    gap, header = max(panel_w * 0.03, 30), 70

    def uri(text: str) -> str:
        encoded = base64.b64encode(text.encode("utf-8")).decode("ascii")
        return "data:image/svg+xml;base64," + encoded

    width = panel_w * 2 + gap
    height = panel_h + header
    comparison = (
        '<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width:g} {height:g}">'
        '<rect width="100%" height="100%" fill="#111827"/>'
        f'<text x="{panel_w/2:g}" y="42" text-anchor="middle" '
        'fill="white" font-family="sans-serif" font-size="28">BEFORE</text>'
        f'<text x="{panel_w+gap+panel_w/2:g}" y="42" text-anchor="middle" '
        'fill="white" font-family="sans-serif" font-size="28">AFTER</text>'
        f'<image href="{uri(before_text)}" x="0" y="{header}" '
        f'width="{panel_w:g}" height="{panel_h:g}" preserveAspectRatio="xMidYMid meet"/>'
        f'<image href="{uri(after_text)}" x="{panel_w+gap:g}" y="{header}" '
        f'width="{panel_w:g}" height="{panel_h:g}" preserveAspectRatio="xMidYMid meet"/>'
        '</svg>'
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(comparison, encoding="utf-8")
    before_hash = hashlib.sha256(before_text.encode()).hexdigest()
    after_hash = hashlib.sha256(after_text.encode()).hexdigest()
    return {
        "ok": True, "comparison_svg": str(output),
        "changed": before_hash != after_hash,
        "before_sha256": before_hash, "after_sha256": after_hash,
        "before_structured_groups": len(_DATA_OBJECT.findall(before_text)),
        "after_structured_groups": len(_DATA_OBJECT.findall(after_text)),
    }
