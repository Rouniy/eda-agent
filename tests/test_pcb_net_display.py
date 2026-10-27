# SPDX-License-Identifier: Apache-2.0
"""Net display reads and writes are board-scoped and preconditioned."""

import asyncio

from eda_agent.tools import pcb


PATH = r"D:\scratch\Board.PcbDoc"
ROW = {"net": "GND", "connections_shown": True,
       "loop_removal": True, "use_net_color": False,
       "jumpers_shown": False, "in_differential_pair": False}


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

    async def send_command_async(self, name, params, timeout=None):
        self.calls.append((name, params))
        return self.replies[len(self.calls) - 1]


def _tool(monkeypatch, replies):
    bridge = _Bridge(replies)
    monkeypatch.setattr(pcb, "get_bridge", lambda: bridge)
    mcp = _Mcp()
    pcb.register_pcb_tools(mcp)
    return mcp.tools["pcb_net_display"], bridge


def _read():
    return {"board_path": PATH, "count": 1, "before_bits": "1100",
            "wrote": False, "nets": [ROW], "before": [ROW]}


def test_read_and_dry_run_do_not_write(monkeypatch):
    tool, bridge = _tool(monkeypatch, [_read()])
    assert asyncio.run(tool(PATH, ["GND"]))["nets"] == [ROW]
    assert bridge.calls == [("pcb.net_display", {"board_path": PATH, "nets": "GND"})]
    tool, bridge = _tool(monkeypatch, [_read()])
    plan = asyncio.run(tool(PATH, ["GND"], show_connections=False))
    assert plan["dry_run"] and plan["would_set"] == {"show_connections": False}
    assert len(bridge.calls) == 1


def test_write_carries_old_bits_and_checks_readback(monkeypatch):
    written = {**_read(), "wrote": True,
               "nets": [{**ROW, "connections_shown": False}], "applied_count": 1}
    tool, bridge = _tool(monkeypatch, [_read(), written])
    result = asyncio.run(tool(PATH, ["GND"], show_connections=False, dry_run=False))
    assert result["nets"][0]["connections_shown"] is False
    assert bridge.calls[1] == ("pcb.net_display", {
        "board_path": PATH, "nets": "GND", "expected_bits": "1100",
        "show_connections": "false"})
    tool, _ = _tool(monkeypatch, [_read(), {**written, "nets": [ROW]}])
    assert asyncio.run(tool(PATH, ["GND"], show_connections=False, dry_run=False))["ok"] is False


def test_incomplete_read_and_duplicate_nets_are_refused(monkeypatch):
    tool, bridge = _tool(monkeypatch, [{**_read(), "count": 2}])
    assert asyncio.run(tool(PATH, ["GND"], dry_run=False))["ok"] is False
    assert len(bridge.calls) == 1
    tool, bridge = _tool(monkeypatch, [_read()])
    assert asyncio.run(tool(PATH, ["GND", "gnd"]))["ok"] is False
    assert not bridge.calls
