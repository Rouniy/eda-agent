# SPDX-License-Identifier: Apache-2.0
"""Whole-footprint rotation plans and verifies every supported object."""

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

    async def send_command_async(self, command, params, timeout=None):
        self.calls.append((command, params))
        return self.replies[len(self.calls) - 1]


def _tool(monkeypatch, replies):
    bridge = _Bridge(replies)
    monkeypatch.setattr(library, "get_bridge", lambda: bridge)
    mcp = _Mcp()
    library.register_library_tools(mcp)
    return mcp.tools["lib_rotate_footprint"], bridge


def _plan(path, **extra):
    return {"library_path": str(path), "footprint": "PART", "angle": 90,
            "dry_run": True, "kinds": {"pads": 2, "tracks": 1, "arcs": 0,
                                          "fills": 0, "regions": 0, "vias": 0,
                                          "texts": 1, "bodies": 1},
            "not_turned": 0, "turned": 0, "mismatches": 0,
            "pad_mismatches": [], "bodies_with_models": 1, **extra}


def test_dry_run_and_verified_rotation(tmp_path, monkeypatch):
    path = tmp_path / "test.PcbLib"
    path.touch()
    tool, bridge = _tool(monkeypatch, [{"success": True}, _plan(path)])
    assert asyncio.run(tool(str(path), "PART", 90))["dry_run"] is True
    assert [c[0] for c in bridge.calls] == ["application.open_document",
                                           "library.rotate_footprint"]
    write = {**_plan(path), "dry_run": False, "turned": 5}
    tool, bridge = _tool(monkeypatch, [{"success": True}, _plan(path), write])
    assert asyncio.run(tool(str(path), "PART", 90, dry_run=False))["save_required"]
    assert bridge.calls[2][1]["dry_run"] == "false"


def test_partial_or_mismatched_rotation_is_not_reported_as_success(tmp_path, monkeypatch):
    path = tmp_path / "test.PcbLib"
    path.touch()
    plan = _plan(path, not_turned=1)
    tool, bridge = _tool(monkeypatch, [{"success": True}, plan])
    assert asyncio.run(tool(str(path), "PART", 90, dry_run=False))["ok"] is False
    assert len(bridge.calls) == 2
    plan = _plan(path)
    reply = {**plan, "dry_run": False, "turned": 5,
             "mismatches": 1, "pad_mismatches": [{"pad": "1"}]}
    tool, _ = _tool(monkeypatch, [{"success": True}, plan, reply])
    result = asyncio.run(tool(str(path), "PART", 90, dry_run=False))
    assert result["ok"] is False and result["save_required"] is True


def test_invalid_angle_refused_before_open(tmp_path, monkeypatch):
    path = tmp_path / "test.PcbLib"
    path.touch()
    tool, bridge = _tool(monkeypatch, [])
    assert asyncio.run(tool(str(path), "PART", 45))["ok"] is False
    assert not bridge.calls
