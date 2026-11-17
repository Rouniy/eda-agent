# SPDX-License-Identifier: Apache-2.0
"""pcb_add_layer refuses a layer the stack already holds.

Measured 2026-11-17 on a four-layer board: asking for MidLayer1 again
changed nothing, the reply said success, and the save-and-reopen that
follows reported "the save did not reach the file" for a board that had
nothing to save.
"""
from pathlib import Path

from tests.pascal_source import load

PCB = Path(__file__).resolve().parents[1] / "scripts" / "altium" / "PCB.pas"


def test_the_stack_is_walked_before_the_edit_opens():
    body = load(PCB)["PCB_AddLayer"]
    refuse = body.index("'ALREADY_IN_STACK'")
    assert refuse < body.index("PcbBeginEdit(0);")
    assert "If Walk.Name = NewObj.Name Then" in body[:refuse]
    assert "nothing was changed" in body


def test_the_new_layer_is_given_a_copper_thickness():
    """Altium inserts it at 0, and a saved stack then carries a copper
    layer with no thickness."""
    body = load(PCB)["PCB_AddLayer"]
    insert = body.index("LayerStack.InsertInStackBelow(RefObj, NewObj)")
    assert "If NewObj.CopperThickness = 0 Then" in body[insert:]
    assert "NewObj.CopperThickness := Thick;" in body[insert:]
    assert "copper_thickness_taken_from_first_layer" in body
