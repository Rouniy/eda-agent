# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 George Saliba <george.saliba@salitronic.com>
"""Legacy image export verifies files and refuses direct PDF preview."""
from __future__ import annotations

import asyncio

from eda_agent.tools import project as project_tools


class _Mcp:
    def __init__(self):
        self.tools = {}

    def tool(self, *args, **kwargs):
        def register(fn):
            self.tools[fn.__name__] = fn
            return fn
        return register


class _Bridge:
    async def send_command_async(self, command, params=None, timeout=None):
        return {"success": True, "output_path": (params or {}).get("output_path")}


def _export(monkeypatch, path, format="png"):
    monkeypatch.setattr(project_tools, "get_bridge", lambda: _Bridge())
    mcp = _Mcp()
    project_tools.register_project_tools(mcp)
    return asyncio.run(mcp.tools["proj_export_image"](str(path), format=format))


def test_a_real_image_passes(monkeypatch, tmp_path):
    out_file = tmp_path / "sheet.png"
    out_file.write_bytes(b"\x89PNG\r\n\x1a\n...")
    out = _export(monkeypatch, out_file)
    assert out["success"] is True and out["file_exists"] is True


def test_direct_pdf_refuses_without_claiming_a_print(monkeypatch, tmp_path):
    out_file = tmp_path / "sheet.pdf"
    out_file.write_bytes(b"")
    out = _export(monkeypatch, out_file, format="pdf")
    assert out["success"] is False
    assert out["error"]["code"] == "PREVIEW_NOT_SILENT"


def test_a_missing_file_is_still_reported(monkeypatch, tmp_path):
    out = _export(monkeypatch, tmp_path / "never.png")
    assert out["error"] == "EXPORT_FILE_MISSING"
