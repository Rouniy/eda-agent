# SPDX-License-Identifier: Apache-2.0
"""A custom footprint uses one native creation call and exact readback."""

import asyncio

from eda_agent.tools import library


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
    monkeypatch.setattr(library, "get_bridge", lambda: bridge)
    mcp = _Mcp()
    library.register_library_tools(mcp)
    return mcp.tools["lib_create_pcb_footprint"], bridge


PADS = [
    {"designator": "1", "x_mm": -1.25, "y_mm": 0.5,
     "x_size_mm": 0.6, "y_size_mm": 1.2, "shape": "rect"},
    {"designator": "2", "x_mm": 1.25, "y_mm": 0.5,
     "x_size_mm": 0.6, "y_size_mm": 1.2, "shape": "oval"},
]


def test_custom_footprint_plan_and_one_guarded_write(monkeypatch, tmp_path):
    path = str(tmp_path / "Parts.PcbLib")
    (tmp_path / "Parts.PcbLib").write_bytes(b"library")
    plan = {"library_path": path, "name": "TEST2", "footprint_count": 5,
            "pad_count": 2, "wrote": False, "body_mm": [-2, -1, 2, 1]}
    written = {"library_path": path, "name": "TEST2", "footprint_count_before": 5,
               "pad_count": 2, "wrote": True, "body_mm": [-2, -1, 2, 1]}
    readback = {"library_path": path, "name": "TEST2", "pad_count": 2,
                "pads": [{"name": "1", "x_mm": -1.25, "y_mm": 0.5,
                          "w_mm": 0.6, "h_mm": 1.2, "shape": "rectangular"},
                         {"name": "2", "x_mm": 1.25, "y_mm": 0.5,
                          "w_mm": 0.6, "h_mm": 1.2, "shape": "round"}]}
    primitives = {"library_path": path, "name": "TEST2",
                  "tracks": ([{"layer": "TopOverlay"}] * 5
                             + [{"layer": "Mechanical13"}] * 4
                             + [{"layer": "Mechanical15"}] * 4),
                  "arcs": [{}], "texts": [{"text": ".Designator"}]}
    tool, bridge = _tool(monkeypatch, [plan])
    dry = asyncio.run(tool(path, "TEST2", PADS))
    assert dry["dry_run"] and len(bridge.calls) == 1
    tool, bridge = _tool(monkeypatch, [plan, written, readback, primitives])
    result = asyncio.run(tool(path, "TEST2", PADS, dry_run=False))
    assert result["ok"] and result["save_required"]
    assert [name for name, _ in bridge.calls] == [
        "library.create_pcb_footprint", "library.create_pcb_footprint",
        "library.get_pad_geometry", "library.get_footprint_primitives"]
    assert bridge.calls[1][1]["expected_count"] == "5"
    assert bridge.calls[1][1]["pads"] == bridge.calls[0][1]["pads"]


def test_custom_footprint_rejects_duplicate_pad_before_native(monkeypatch, tmp_path):
    path = str(tmp_path / "Parts.PcbLib")
    (tmp_path / "Parts.PcbLib").write_bytes(b"library")
    tool, bridge = _tool(monkeypatch, [])
    result = asyncio.run(tool(path, "TEST2", [PADS[0], {**PADS[1], "designator": "1"}]))
    assert result["ok"] is False and not bridge.calls


def test_custom_footprint_refuses_wrong_library_reply(monkeypatch, tmp_path):
    path = str(tmp_path / "Parts.PcbLib")
    (tmp_path / "Parts.PcbLib").write_bytes(b"library")
    tool, bridge = _tool(monkeypatch, [{"library_path": str(tmp_path / "Other.PcbLib"),
                                        "name": "TEST2", "footprint_count": 5,
                                        "pad_count": 2, "wrote": False}])
    result = asyncio.run(tool(path, "TEST2", PADS, dry_run=False))
    assert result["ok"] is False and len(bridge.calls) == 1
