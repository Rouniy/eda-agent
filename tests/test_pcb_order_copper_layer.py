# SPDX-License-Identifier: Apache-2.0
"""Copper-layer insertion checks native IDs and verifies final order."""

import asyncio

from eda_agent.tools import pcb


BOARD = r"D:\scratch\Board.PcbDoc"
BEFORE = ["Top Layer", "Int1", "Int2", "Bottom Layer"]
CANONICAL = ["TopLayer", "MidLayer1", "MidLayer2", "BottomLayer"]


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
        self.replies = iter(replies)
        self.calls = []

    async def send_command_async(self, command, params, timeout=None):
        self.calls.append((command, params))
        return next(self.replies)


def _tool(monkeypatch, replies):
    bridge = _Bridge(replies)
    monkeypatch.setattr(pcb, "get_bridge", lambda: bridge)
    mcp = _Mcp()
    pcb.register_pcb_tools(mcp)
    return mcp.tools["pcb_order_copper_layer"], bridge


def _snapshot(order=BEFORE, canonical=CANONICAL, board=BOARD):
    return {"board_path": board, "count": len(order), "order": order,
            "canonical_order": canonical, "order_token": "TOKEN"}


def test_existing_renamed_layer_id_refuses_insertion(monkeypatch):
    tool, bridge = _tool(monkeypatch, [_snapshot()])
    result = asyncio.run(tool(BOARD, "insert", "MidLayer1", above="Int2",
                              dry_run=False))
    assert result["ok"] is False
    assert len(bridge.calls) == 1


def test_insert_with_reference_and_independent_readback(monkeypatch):
    after = ["Top Layer", "Int1", "MidLayer3", "Int2", "Bottom Layer"]
    native = {"board_path": BOARD, "target_name": "MidLayer3",
              "reference_name": "Int2", "position": "above", "changed": True,
              "order_before": BEFORE, "order_after": after}
    tool, bridge = _tool(monkeypatch, [
        _snapshot(), native,
        _snapshot(after, ["TopLayer", "MidLayer1", "MidLayer3",
                          "MidLayer2", "BottomLayer"]),
    ])
    result = asyncio.run(tool(BOARD, "insert", "MidLayer3", above="Int2",
                              dry_run=False))
    assert result["save_required"] is True
    assert bridge.calls[1][1]["expect_order"] == "TOKEN"


def test_wrong_board_and_failed_position_refused(monkeypatch):
    tool, bridge = _tool(monkeypatch, [_snapshot(board=r"D:\other.PcbDoc")])
    assert asyncio.run(tool(BOARD))["ok"] is False
    assert len(bridge.calls) == 1
    after = ["Top Layer", "Int1", "Int2", "Bottom Layer", "MidLayer3"]
    native = {"board_path": BOARD, "target_name": "MidLayer3",
              "reference_name": "Int2", "position": "above", "changed": True,
              "order_before": BEFORE, "order_after": after}
    tool, _ = _tool(monkeypatch, [_snapshot(), native, _snapshot(after,
                    CANONICAL + ["MidLayer3"])])
    assert asyncio.run(tool(BOARD, "insert", "MidLayer3", above="Int2",
                            dry_run=False))["ok"] is False


def test_move_named_layer_below_reference(monkeypatch):
    before = ["Top Layer", "Int1", "Mid-Layer 3", "Int2", "Bottom Layer"]
    after = ["Top Layer", "Int1", "Int2", "Mid-Layer 3", "Bottom Layer"]
    canonical_before = ["TopLayer", "MidLayer1", "MidLayer3",
                        "MidLayer2", "BottomLayer"]
    canonical_after = ["TopLayer", "MidLayer1", "MidLayer2",
                       "MidLayer3", "BottomLayer"]
    native = {"board_path": BOARD, "target_name": "Mid-Layer 3",
              "reference_name": "Int2", "position": "below", "changed": True,
              "order_before": before, "order_after": after}
    tool, bridge = _tool(monkeypatch, [
        _snapshot(before, canonical_before), native,
        _snapshot(after, canonical_after),
    ])
    result = asyncio.run(tool(BOARD, "move", "Mid-Layer 3", below="Int2",
                              dry_run=False))
    assert result["save_required"] is True
    assert bridge.calls[1][1]["below"] == "Int2"


def test_already_adjacent_move_is_noop(monkeypatch):
    order = ["Top Layer", "Int1", "Int2", "Mid-Layer 3", "Bottom Layer"]
    canonical = ["TopLayer", "MidLayer1", "MidLayer2", "MidLayer3", "BottomLayer"]
    tool, bridge = _tool(monkeypatch, [_snapshot(order, canonical)])
    result = asyncio.run(tool(BOARD, "move", "Mid-Layer 3", below="Int2",
                              dry_run=False))
    assert result["changed"] is False
    assert len(bridge.calls) == 1
