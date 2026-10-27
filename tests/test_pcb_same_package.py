# SPDX-License-Identifier: Apache-2.0
"""Package grouping requires one identified and complete native board read."""

import asyncio

from eda_agent.tools import pcb


PATH = r"D:\scratch\Board.PcbDoc"


class _Mcp:
    def __init__(self):
        self.tools = {}

    def tool(self, *args, **kwargs):
        def register(fn):
            self.tools[fn.__name__] = fn
            return fn
        return register


class _Bridge:
    def __init__(self, reply):
        self.reply = reply
        self.calls = []

    async def send_command_async(self, name, params, timeout=None):
        self.calls.append((name, params))
        return self.reply


def _tool(monkeypatch, reply):
    bridge = _Bridge(reply)
    monkeypatch.setattr(pcb, "get_bridge", lambda: bridge)
    mcp = _Mcp()
    pcb.register_pcb_tools(mcp)
    return mcp.tools["pcb_find_same_package"], bridge


def test_exact_board_groups_include_unhashed_parts(monkeypatch):
    reply = {"board_path": PATH, "parts_examined": 3,
             "parts_without_hash": 2, "compare_errors": 0,
             "group_count": 1,
             "groups": [{"footprint": "0603", "count": 2,
                         "designators": ["R1", "R2"]}]}
    tool, bridge = _tool(monkeypatch, reply)
    assert asyncio.run(tool(PATH))["groups"] == reply["groups"]
    assert bridge.calls == [("pcb.find_same_package", {"board_path": PATH})]


def test_comparison_failure_and_wrong_board_are_refused(monkeypatch):
    for reply in ({"board_path": PATH, "parts_examined": 2,
                   "compare_errors": 1, "group_count": 0, "groups": []},
                  {"board_path": r"D:\scratch\Other.PcbDoc", "parts_examined": 0,
                   "compare_errors": 0, "group_count": 0, "groups": []}):
        tool, _ = _tool(monkeypatch, reply)
        assert asyncio.run(tool(PATH))["ok"] is False


def test_designator_read_and_relative_path(monkeypatch):
    reply = {"board_path": PATH, "parts_examined": 2,
             "compare_errors": 0, "same_package": ["R2"]}
    tool, bridge = _tool(monkeypatch, reply)
    assert asyncio.run(tool(PATH, "R1"))["same_package"] == ["R2"]
    assert bridge.calls == [("pcb.find_same_package", {
        "board_path": PATH, "designator": "R1"})]
    assert asyncio.run(tool("Board.PcbDoc"))["ok"] is False
    assert len(bridge.calls) == 1
