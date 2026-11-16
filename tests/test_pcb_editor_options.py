# SPDX-License-Identifier: Apache-2.0
"""Global PCB preferences use an exact board and old-value preflight."""

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
    def __init__(self, replies):
        self.replies = replies
        self.calls = []

    async def send_command_async(self, command, params, timeout=None):
        self.calls.append((command, params))
        return self.replies[len(self.calls) - 1]


def _tools(monkeypatch, replies):
    bridge = _Bridge(replies)
    monkeypatch.setattr(pcb, "get_bridge", lambda: bridge)
    mcp = _Mcp()
    pcb.register_pcb_tools(mcp)
    return mcp.tools, bridge


def _read(names, **extra):
    options = {native: (0 if key in pcb._PCB_OPTION_INTS else
                        0.0 if key in pcb._PCB_OPTION_FLOATS else False)
               for key, native in names.items()}
    return {"board_path": PATH, "options": options, "changed": False,
            "not_applied": [], "refused": [], "unknown": [], **extra}


def test_read_plan_and_verified_write(monkeypatch):
    names = pcb._PCB_VIEW_OPTIONS
    old = _read(names)
    tools, bridge = _tools(monkeypatch, [old])
    plan = asyncio.run(tools["pcb_view_options"](PATH, show_pad_nets=True))
    assert plan["dry_run"] and plan["would_set"] == {"show_pad_nets": True}
    assert len(bridge.calls) == 1
    new = _read(names, options={**old["options"], "ShowPadNets": True}, changed=True)
    tools, bridge = _tools(monkeypatch, [old, new])
    result = asyncio.run(tools["pcb_view_options"](
        PATH, show_pad_nets=True, dry_run=False))
    assert result["options"]["show_pad_nets"] is True
    assert "ShowPadNets=false" in bridge.calls[1][1]["expect"]
    assert bridge.calls[1][1]["set"] == "ShowPadNets=true"


def test_wrong_board_and_partial_read_refuse_before_write(monkeypatch):
    names = pcb._PCB_ROUTE_OPTIONS
    for bad in (_read(names, board_path=r"D:\other.PcbDoc"),
                _read(names, options={})):
        tools, bridge = _tools(monkeypatch, [bad])
        assert asyncio.run(tools["pcb_route_options"](
            PATH, auto_via=True, dry_run=False))["ok"] is False
        assert len(bridge.calls) == 1


def test_invalid_types_refuse_without_native_call(monkeypatch):
    tools, bridge = _tools(monkeypatch, [])
    assert asyncio.run(tools["pcb_route_options"](PATH, route_mode=-1))["ok"] is False
    assert asyncio.run(tools["pcb_edit_options"](PATH, rotation_step=float("nan")))["ok"] is False
    assert not bridge.calls
