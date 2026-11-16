# SPDX-License-Identifier: Apache-2.0
"""A moved courtyard must differ even when primitive counts still match."""

from __future__ import annotations

import asyncio

from eda_agent.tools import library


def test_live_compare_detects_a_moved_courtyard(monkeypatch):
    calls = []

    class Bridge:
        async def send_command_async(self, command, params):
            calls.append((command, params))
            path = params["library_path"]
            if command == "library.get_pad_geometry":
                return {"name": params["footprint_name"],
                        "library_path": path, "pads": []}
            if command == "library.get_footprint_primitives":
                y = 1.0 if path == "C:/a.PcbLib" else 1.5
                return {"name": params["footprint_name"],
                        "library_path": path, "height_mm": 0,
                        "tracks": [{"layer": "Mechanical1", "x1": -1,
                                    "y1": y, "x2": 1, "y2": y, "width": 0.1}],
                        "body_models": []}
            if command == "library.get_mech_layers":
                return {"library_path": path,
                        "layers": [{"layer": "Mechanical1",
                                    "kind": "Courtyard Top"}]}
            raise AssertionError(command)

    class Registry:
        def tool(self, *args, **kwargs):
            def register(fn):
                tools[fn.__name__] = fn
                return fn
            return register

    tools = {}
    monkeypatch.setattr(library, "get_bridge", lambda: Bridge())
    library.register_library_tools(Registry())
    compare = tools["lib_compare_footprints"]

    changed = asyncio.run(compare("FP", "FP", "C:/a.PcbLib", "C:/b.PcbLib"))
    assert changed["ok"] and not changed["identical"]
    assert changed["primitives"] == {}, "both have one track on the same layer"
    assert "courtyard" in changed["geometry"]["layers_differing"]
    assert [params["library_path"] for command, params in calls
            if command == "library.get_mech_layers"] == ["C:/a.PcbLib", "C:/b.PcbLib"]

    tolerated = asyncio.run(compare("FP", "FP", "C:/a.PcbLib", "C:/b.PcbLib",
                                    tolerance_mm=0.5))
    assert tolerated["identical"]
