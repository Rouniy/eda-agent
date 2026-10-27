# SPDX-License-Identifier: Apache-2.0
"""A free schematic label is a distinct, exact-sheet object."""

import asyncio

from eda_agent.tools import generic
from tests.test_gap_fixes import _capture


SHEET = r"D:\scratch\Notes.SchDoc"


class Bridge:
    def __init__(self, reply=None):
        self.calls = []
        self.reply = reply or {"placed": True, "sheet_path": SHEET, "text": "REV A",
                               "x": 125.5, "y": 200.25, "rotation": 90}

    async def send_command_async(self, command, params, **kwargs):
        self.calls.append((command, params))
        return self.reply


def test_free_text_uses_exact_sheet_and_preserves_text(monkeypatch):
    bridge = Bridge()
    monkeypatch.setattr(generic, "get_bridge", lambda: bridge)
    tool = _capture(generic, "register_generic_tools")["sch_add_text"]
    result = asyncio.run(tool("REV A", 125.5, 200.25, 90, SHEET))
    assert result["save_required"] is True
    assert bridge.calls == [("generic.place_free_text", {
        "sheet_path": SHEET, "text": "REV A", "x": "125.5",
        "y": "200.25", "rotation": 1, "font_id": 0})]


def test_free_text_refuses_bad_input_and_wrong_sheet_reply(monkeypatch):
    bridge = Bridge({"sheet_path": r"D:\other.SchDoc", "text": "REV A",
                     "x": 125.5, "y": 200.25, "rotation": 90})
    monkeypatch.setattr(generic, "get_bridge", lambda: bridge)
    tool = _capture(generic, "register_generic_tools")["sch_add_text"]
    for kwargs in ({"sheet_path": "Notes.SchDoc"},
                   {"sheet_path": SHEET, "rotation": 45},
                   {"sheet_path": SHEET, "x": float("nan")},
                   {"sheet_path": SHEET, "text": "two\nlines"},
                   {"sheet_path": SHEET, "text": "10Ω"}):
        args = {"text": "REV A", "x": 125.5, "y": 200.25,
                "rotation": 90, "sheet_path": SHEET, **kwargs}
        assert asyncio.run(tool(**args))["ok"] is False
    assert bridge.calls == []
    result = asyncio.run(tool("REV A", 125.5, 200.25, 90, SHEET))
    assert result["ok"] is False
    assert len(bridge.calls) == 1
