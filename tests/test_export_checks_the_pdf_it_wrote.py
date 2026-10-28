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
    def __init__(self):
        self.calls = []

    async def send_command_async(self, command, params=None, timeout=None):
        self.calls.append((command, params))
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


def test_direct_pdf_opt_in_requires_new_path_and_checks_result(monkeypatch, tmp_path):
    bridge = _Bridge()
    monkeypatch.setattr(project_tools, "get_bridge", lambda: bridge)
    mcp = _Mcp()
    project_tools.register_project_tools(mcp)
    output = tmp_path / "sheet.pdf"

    refused = asyncio.run(mcp.tools["proj_export_pdf"](str(output)))
    assert refused["error"]["code"] == "PREVIEW_NOT_SILENT"
    assert bridge.calls == []

    output.write_bytes(b"old PDF")
    refused = asyncio.run(mcp.tools["proj_export_pdf"](
        str(output), open_print_dialog=True))
    assert refused["error"]["code"] == "OUTPUT_PATH_EXISTS"
    assert output.read_bytes() == b"old PDF"
    assert bridge.calls == []

    output.unlink()
    result = asyncio.run(mcp.tools["proj_export_pdf"](
        str(output), open_print_dialog=True))
    assert bridge.calls == [("project.export_pdf", {"output_path": str(output)})]
    assert result["success"] is False
    assert result["error"] == "EXPORT_FILE_INVALID"


def test_image_pdf_opt_in_keeps_existing_file(monkeypatch, tmp_path):
    bridge = _Bridge()
    monkeypatch.setattr(project_tools, "get_bridge", lambda: bridge)
    mcp = _Mcp()
    project_tools.register_project_tools(mcp)
    output = tmp_path / "sheet.pdf"
    output.write_bytes(b"old PDF")

    result = asyncio.run(mcp.tools["proj_export_image"](
        str(output), format="pdf", open_print_dialog=True))
    assert result["error"]["code"] == "OUTPUT_PATH_EXISTS"
    assert output.read_bytes() == b"old PDF"
    assert bridge.calls == []


def test_a_missing_file_is_still_reported(monkeypatch, tmp_path):
    out = _export(monkeypatch, tmp_path / "never.png")
    assert out["error"] == "EXPORT_FILE_MISSING"
