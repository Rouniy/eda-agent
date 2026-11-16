# SPDX-License-Identifier: Apache-2.0
"""Body edits preserve saved STEP orientation and check native readback."""

import asyncio

from eda_agent.fileio import altium_pcblib
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

    async def send_command_async(self, command, params, timeout=None):
        self.calls.append((command, params))
        return self.replies[len(self.calls) - 1]


def _tool(monkeypatch, replies):
    bridge = _Bridge(replies)
    monkeypatch.setattr(library, "get_bridge", lambda: bridge)
    mcp = _Mcp()
    library.register_library_tools(mcp)
    return mcp.tools["lib_set_3d_body"], bridge


def _body():
    return {"index": 1, "layer": "Mechanical1", "step": True,
            "standoff_height_mils": 0.0,
            "overall_height_mils": 100.0, "opacity": 1.0}


def _read(path):
    return {"library": str(path), "footprint": "PART", "bodies": 1,
            "changed": 0, "before": [_body()], "after": [_body()],
            "skipped": [], "model_z_offset_written": []}


def _live(path):
    return {"library_path": str(path), "name": "PART", "bodies": 1,
            "body_models": [{"layer": "Mechanical1", "model_type": 1,
                             "model_file": str(path.parent / "part.step")}]}


def test_saved_body_parser_preserves_model_name_rotation_and_offset():
    data = (b"\x00|MODEL.NAME=part.step|MODEL.MODELTYPE=1|"
            b"MODEL.3D.ROTX=90|MODEL.3D.ROTY=-5|MODEL.3D.ROTZ=270|"
            b"MODEL.3D.DZ=0.254mm\x00")
    found = altium_pcblib._saved_body_records(data)
    assert found[0]["model_file"] == "part.step"
    assert found[0]["rotation_deg"] == [90, -5, 270]
    assert abs(found[0]["model_z_offset_mils"] - 10) < 1e-6
