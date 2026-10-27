# SPDX-License-Identifier: Apache-2.0
"""Native rule answers must identify the exact board and carry real results."""

import asyncio

from eda_agent.tools import pcb


PATH = r"D:\scratch\Rules.PcbDoc"


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

    async def send_command_async(self, command, params, timeout=None):
        self.calls.append((command, params))
        return self.reply


def _tools(monkeypatch, reply):
    bridge = _Bridge(reply)
    monkeypatch.setattr(pcb, "get_bridge", lambda: bridge)
    mcp = _Mcp()
    pcb.register_pcb_tools(mcp)
    return mcp.tools, bridge


def test_dominant_rule_requires_kind_and_exact_reply(monkeypatch):
    tools, bridge = _tools(monkeypatch, {})
    assert asyncio.run(tools["pcb_find_dominant_rule"](PATH, "U1"))["ok"] is False
    assert not bridge.calls
    tools, bridge = _tools(monkeypatch, {"board_path": PATH, "found": False,
                                        "rule_kind": 5})
    result = asyncio.run(tools["pcb_find_dominant_rule"](
        PATH, "U1.3", rule_kind=5))
    assert result["found"] is False
    assert bridge.calls[0] == ("pcb.find_dominant_rule",
                               {"board_path": PATH, "object1": "U1.3",
                                "rule_kind": "5"})
    tools, _ = _tools(monkeypatch, {"board_path": r"D:\other.PcbDoc",
                                  "found": False, "rule_kind": 5})
    assert asyncio.run(tools["pcb_find_dominant_rule"](
        PATH, "U1", rule_kind=5))["ok"] is False


def test_scope_requires_complete_native_flags(monkeypatch):
    good = {"board_path": PATH, "rule": {"name": "Width"}, "unary": True,
            "scope1_includes_object1": True,
            "scope2_includes_object2": False, "applies": True}
    tools, bridge = _tools(monkeypatch, good)
    assert asyncio.run(tools["pcb_check_rule_scope"](
        PATH, "Width", "U1"))["applies"] is True
    assert bridge.calls[0][0] == "pcb.rule_scope_check"
    tools, _ = _tools(monkeypatch, {**good, "applies": None})
    assert asyncio.run(tools["pcb_check_rule_scope"](
        PATH, "Width", "U1"))["ok"] is False
