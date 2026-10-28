# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 George Saliba <george.saliba@salitronic.com>
"""Variant publishing uses staged OutJobs and leaves the source variant alone."""

from __future__ import annotations

from configparser import ConfigParser
from pathlib import Path

import pytest
from pypdf import PdfWriter

from eda_agent.tools import project as project_module


def _capture(monkeypatch, bridge):
    monkeypatch.setattr(project_module, "get_bridge", lambda: bridge)
    captured = {}

    class DummyMcp:
        def tool(self, *a, **k):
            def deco(fn):
                captured[fn.__name__] = fn
                return fn
            return deco

    project_module.register_project_tools(DummyMcp())
    return captured["proj_print_all_variants"]


class _Bridge:
    def __init__(self, source: Path, *, fail_run=False,
                 fail_final_readback=False):
        self.source = source
        self.fail_run = fail_run
        self.fail_final_readback = fail_final_readback
        self.calls = []

    async def send_command_async(self, command, params=None, timeout=None):
        params = params or {}
        self.calls.append((command, params))
        if command == "project.get_variants":
            return {"variants": [{"name": "Assembly-A"},
                                 {"name": "Assembly-B"}]}
        if command == "project.get_active_variant":
            assert params.get("project_path") == str(self.source)
            reads = sum(c == command for c, _ in self.calls)
            if self.fail_final_readback and reads > 1:
                raise RuntimeError("readback unavailable")
            return {"name": "Assembly-A"}
        if command == "application.get_active_document":
            return {"file_path": str(self.source.parent / "Top.SchDoc")}
        if command in ("project.open", "application.open_document",
                       "application.set_active_document"):
            return {"success": True}
        if command == "project.run_outjob":
            if self.fail_run:
                return {"process_issued": False}
            job = ConfigParser(interpolation=None)
            job.read(params["outjob_path"], encoding="utf-8")
            chosen = job["OutputGroup1"]["VariantName"]
            assert chosen in ("Assembly-A", "Assembly-B")
            assert job["OutputGroup1"]["OutputVariantName1"] == chosen
            pdf = Path(job["PublishSettings"]["OutputFilePath1"])
            writer = PdfWriter()
            writer.add_blank_page(width=72, height=72)
            with pdf.open("wb") as out:
                writer.write(out)
            return {"process_issued": True}
        if command == "project.get_documents":
            return {"documents": []}
        if command == "project.close":
            return {"success": True, "closed": True, "closed_instead": []}
        raise AssertionError(f"unexpected command: {command}")


def _source(tmp_path: Path) -> Path:
    source = tmp_path / "source" / "Sample.PrjPcb"
    source.parent.mkdir()
    (source.parent / "Top.SchDoc").write_bytes(b"schematic")
    source.write_text(
        "[Design]\nVersion=1.0\n"
        "[Document1]\nDocumentPath=Top.SchDoc\n"
        "[Variant1]\nName=Assembly-A\n"
        "[Variant2]\nName=Assembly-B\n",
        encoding="utf-8",
    )
    return source


@pytest.mark.asyncio
async def test_exports_real_pdfs_without_switching_source(monkeypatch, tmp_path):
    source = _source(tmp_path)
    root = tmp_path / "screens"
    monkeypatch.setenv("EDA_AGENT_SCHEMATIC_PDF_ROOT", str(root))
    bridge = _Bridge(source)
    tool = _capture(monkeypatch, bridge)
    out = await tool(output_dir=str(tmp_path / "published"),
                     project_path=str(source))
    assert out["success"] is True
    assert out["count"] == 2
    assert out["restored"] == "Assembly-A"
    assert [e["page_count"] for e in out["exported"]] == [1, 1]
    for variant in ("Assembly-A", "Assembly-B"):
        assert (tmp_path / "published" / f"{variant}.pdf").read_bytes().startswith(b"%PDF-")
    assert not list(root.glob("_variant_*.pdf"))
    assert all(c != "project.export_pdf" for c, _ in bridge.calls)
    assert all(c != "project.set_active_variant" for c, _ in bridge.calls)


@pytest.mark.asyncio
async def test_failed_first_variant_stops_and_reports_remaining(monkeypatch, tmp_path):
    source = _source(tmp_path)
    monkeypatch.setenv("EDA_AGENT_SCHEMATIC_PDF_ROOT", str(tmp_path / "screens"))
    bridge = _Bridge(source, fail_run=True)
    tool = _capture(monkeypatch, bridge)
    out = await tool(output_dir=str(tmp_path / "published"),
                     project_path=str(source))
    assert out["success"] is False
    assert out["count"] == 0
    assert out["not_run"] == ["Assembly-B"]
    assert out["restored"] == "Assembly-A"
    assert not list((tmp_path / "published").glob("*.pdf"))


@pytest.mark.asyncio
async def test_final_readback_failure_keeps_completed_pdf_report(monkeypatch, tmp_path):
    source = _source(tmp_path)
    monkeypatch.setenv("EDA_AGENT_SCHEMATIC_PDF_ROOT", str(tmp_path / "screens"))
    bridge = _Bridge(source, fail_final_readback=True)
    tool = _capture(monkeypatch, bridge)
    out = await tool(output_dir=str(tmp_path / "published"),
                     project_path=str(source))
    assert out["count"] == 2
    assert out["restored"] is None
    assert out["active_variant_unknown"] is True
    assert "readback unavailable" in out["readback_error"]
