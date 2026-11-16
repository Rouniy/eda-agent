# SPDX-License-Identifier: Apache-2.0
"""Component STEP exports require an exact target and observed STEP bytes."""

import asyncio

from eda_agent.tools import pcb


BOARD = r"D:\scratch\Board.PcbDoc"


class _Mcp:
    def __init__(self):
        self.tools = {}

    def tool(self, *args, **kwargs):
        def register(fn):
            self.tools[fn.__name__] = fn
            return fn
        return register


class _Bridge:
    def __init__(self, board_path, out_path, write_bytes):
        self.board_path = board_path
        self.out_path = out_path
        self.write_bytes = write_bytes
        self.calls = []

    async def send_command_async(self, command, params, timeout=None):
        self.calls.append((command, params))
        if self.write_bytes is not None:
            self.out_path.write_bytes(self.write_bytes)
        return {"board_path": self.board_path, "designator": "U1",
                "out_path": str(self.out_path), "mode": params["mode"],
                "saved": True}


def _tools(monkeypatch, board_path, out_path, write_bytes):
    bridge = _Bridge(board_path, out_path, write_bytes)
    monkeypatch.setattr(pcb, "get_bridge", lambda: bridge)
    mcp = _Mcp()
    pcb.register_pcb_tools(mcp)
    return mcp.tools, bridge


def test_two_export_modes_verify_new_step_file(tmp_path, monkeypatch):
    payload = b"ISO-10303-21;\nHEADER;\nENDSEC;\nEND-ISO-10303-21;\n"
    for name, mode in (("pcb_export_component_model", "part"),
                       ("pcb_export_component_3d", "model")):
        target = tmp_path / f"{mode}.step"
        tools, bridge = _tools(monkeypatch, BOARD, target, payload)
        result = asyncio.run(tools[name](BOARD, "U1", str(target)))
        assert result["written"] and result["bytes"] == len(payload)
        assert len(result["sha256"]) == 64
        assert bridge.calls[0][1]["mode"] == mode
        assert asyncio.run(tools[name](BOARD, "U1", str(target)))["ok"] is False
        assert len(bridge.calls) == 1


def test_wrong_board_or_missing_step_bytes_refuse(tmp_path, monkeypatch):
    target = tmp_path / "bad.step"
    tools, _ = _tools(monkeypatch, r"D:\other.PcbDoc", target, None)
    assert asyncio.run(tools["pcb_export_component_model"](
        BOARD, "U1", str(target)))["ok"] is False
    tools, _ = _tools(monkeypatch, BOARD, target, b"not a STEP file" * 4)
    assert asyncio.run(tools["pcb_export_component_model"](
        BOARD, "U1", str(target)))["ok"] is False
