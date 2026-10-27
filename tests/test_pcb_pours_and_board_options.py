# SPDX-License-Identifier: Apache-2.0
"""PCB pour lookup and exact-board option writes."""

import asyncio

from eda_agent.tools import pcb


class _Mcp:
    def __init__(self):
        self.tools = {}

    def tool(self, *args, **kwargs):
        def register(fn):
            self.tools[fn.__name__] = fn
            return fn
        return register


class _Bridge:
    def __init__(self):
        self.sent = []

    async def send_command_async(self, command, params):
        self.sent.append((command, params))
        return {"success": True, "board_file": r"D:\scratch\board.PcbDoc"}


def test_pour_lookup_sends_coordinates_and_board_identity(monkeypatch):
    bridge = _Bridge()
    monkeypatch.setattr(pcb, "get_bridge", lambda: bridge)
    mcp = _Mcp()
    pcb.register_pcb_tools(mcp)
    out = asyncio.run(mcp.tools["pcb_pours_at"](
        100, 50.5, expect_file=r"D:\scratch\board.PcbDoc"))
    assert out["board_file"].endswith("board.PcbDoc")
    assert bridge.sent == [("pcb.pours_at", {"x": "100.0", "y": "50.5",
                                           "expect_file": r"D:\scratch\board.PcbDoc"})]
    bridge.sent.clear()
    bad = asyncio.run(mcp.tools["pcb_pours_at"](float("nan"), 1))
    assert bad["success"] is False and not bridge.sent


def test_board_option_write_needs_exact_board_and_rejects_bad_values(monkeypatch):
    bridge = _Bridge()
    monkeypatch.setattr(pcb, "get_bridge", lambda: bridge)
    mcp = _Mcp()
    pcb.register_pcb_tools(mcp)
    put = mcp.tools["pcb_board_options"]
    assert asyncio.run(put(polygon_name_template=2))["success"] is False
    assert asyncio.run(put(polygon_name_template=-1,
                           expect_file=r"D:\scratch\board.PcbDoc"))["success"] is False
    assert bridge.sent == []
    asyncio.run(put(polygon_name_template=2,
                    expect_file=r"D:\scratch\board.PcbDoc"))
    assert bridge.sent == [("pcb.board_options", {
        "polygon_name_template": "2",
        "expect_file": r"D:\scratch\board.PcbDoc"})]
