# SPDX-License-Identifier: Apache-2.0
"""The via mask route must avoid the direct property that crashed Altium.

A later AD 26.10 measurement showed that the pad-cache record accepts the
same value and reads it back. The live AD 26.11 check belongs in the release
record; this source check protects the property choice during refactors.
"""

import re
from pathlib import Path

from eda_agent.tools.metadata import tool_metadata
from tests.pascal_source import load

_PCB = Path(__file__).resolve().parents[1] / "scripts" / "altium" / "PCB.pas"


def test_the_handler_avoids_the_crashing_via_property():
    body = load(_PCB, minimum=100)["PCB_SetViaSoldermaskRelief"]
    assert not re.search(r"\bVia\.SolderMaskExpansion\s*:=", body)
    assert "Cache.SolderMaskExpansion := Exp;" in body
    assert "Via.SetState_Cache := Cache;" in body
    assert "WRONG_DOCUMENT_FOCUSED" in body
    assert "GetPCBBoardAnywhere" not in body


def test_the_tool_is_marked_as_a_mutation():
    assert tool_metadata("pcb_set_via_soldermask_relief")["interaction"] == "silent"
