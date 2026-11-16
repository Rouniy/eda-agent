# SPDX-License-Identifier: Apache-2.0
"""A caller can request a bounded native PcbLib primitive walk."""

from __future__ import annotations

import asyncio

from eda_agent.tools import library


def test_kind_selection_reaches_the_native_reader(monkeypatch):
    sent = []

    class Bridge:
        async def send_command_async(self, command, params):
            sent.append((command, params))
            return {"name": "FP", "library_path": "C:/qa.PcbLib",
                    "kinds": params.get("kinds", ""), "body_models": []}

    class Registry:
        def tool(self, *args, **kwargs):
            def register(fn):
                tools[fn.__name__] = fn
                return fn
            return register

    tools = {}
    monkeypatch.setattr(library, "get_bridge", lambda: Bridge())
    library.register_library_tools(Registry())
    read = tools["lib_get_footprint_primitives"]

    selected = asyncio.run(read("FP", "C:/qa.PcbLib", " Via | body | via "))
    assert selected["kinds"] == "via|body"
    assert sent == [("library.get_footprint_primitives",
                     {"footprint_name": "FP", "library_path": "C:/qa.PcbLib",
                      "kinds": "via|body"})]

    refused = asyncio.run(read("FP", kinds="pad|via"))
    assert refused["ok"] is False and refused["invalid_kinds"] == ["pad"]
    assert len(sent) == 1
