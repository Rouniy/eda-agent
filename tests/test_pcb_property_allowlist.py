# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 George Saliba <george.saliba@salitronic.com>
"""Every property the board getter answers is one obj_query accepts.

obj_query refuses a board property IsKnownPCBProperty does not list, so a
name the getter answers but the list lacks is reported as not existing.
Kind, the pour options and the body heights sat in exactly that gap: the
getter read them, the allow-list refused them. KnownPCBPropertyList is the
text the refusal shows, so it has to name them too.
"""

from __future__ import annotations

import re
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "scripts" / "altium" / "PCBGeneric.pas"


def _body(text: str, header: str) -> str:
    start = text.index(header)
    end = re.compile(r"^End;", re.M).search(text, start).end()
    return text[start:end]


def _names(body: str) -> set[str]:
    return set(re.findall(r"PropName\s*=\s*'([A-Za-z.]+)'", body))


def test_the_allow_list_and_the_refusal_text_cover_the_getter():
    text = SOURCE.read_text(encoding="utf-8", errors="replace")
    answered = _names(_body(text, "Function GetPCBProperty("))
    allowed = _names(_body(text, "Function IsKnownPCBProperty("))
    listed = set(re.findall(r"[A-Za-z]+", _body(text, "Function KnownPCBPropertyList(")
                            .split("Begin", 1)[1]))
    assert answered, "the getter's branches were not found; update this test"
    assert answered - allowed == set(), "answered by the getter, refused by obj_query"
    # The refusal text lists bare names; dotted and alias spellings are extra.
    bare = {n for n in answered if "." not in n} - {"RegionKind"}
    assert bare - listed == set(), "missing from the list the refusal shows"


def test_free_copper_can_be_told_from_a_footprints():
    text = SOURCE.read_text(encoding="utf-8", errors="replace")
    answered = _names(_body(text, "Function GetPCBProperty("))
    assert {"InComponent", "InPolygon", "Component", "Locked", "IsKeepout"} <= answered
