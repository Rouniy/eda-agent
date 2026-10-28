# SPDX-License-Identifier: Apache-2.0
"""The silent PDF path must stage a project without touching its source."""

from configparser import ConfigParser
from pathlib import Path

import pytest

from eda_agent.tools.schematic_pdf import (
    checked_output_path,
    remove_stage,
    stage_schematic_project,
)


def test_stages_only_schdocs_under_export_root(tmp_path, monkeypatch):
    root = tmp_path / "screens"
    source = tmp_path / "corpus" / "Sample.PrjPcb"
    (source.parent / "SCH").mkdir(parents=True)
    (source.parent / "SCH" / "Top.SchDoc").write_bytes(b"schematic")
    (source.parent / "Board.PcbDoc").write_bytes(b"board")
    source.write_text(
        "[Design]\nVersion=1.0\n"
        "[Document1]\nDocumentPath=SCH\\Top.SchDoc\n"
        "[Document2]\nDocumentPath=Board.PcbDoc\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("EDA_AGENT_SCHEMATIC_PDF_ROOT", str(root))
    output = root / "result.pdf"
    staged, first_sheet, temporary_pdf, count = stage_schematic_project(
        str(source), str(output))
    assert count == 1
    assert first_sheet.read_bytes() == b"schematic"
    assert not (staged.parent / "Board.PcbDoc").exists()
    assert source.read_text(encoding="utf-8").startswith("[Design]")
    assert temporary_pdf.parent == staged.parent / "output"
    job = (staged.parent / "Documentation.OutJob").read_text(encoding="utf-8")
    assert str(temporary_pdf) in job
    assert "[Project Physical Documents]" in job
    assert "|PrintKind=0|" in next(
        line for line in job.splitlines() if line.startswith("PageOptions1="))
    parsed = ConfigParser(interpolation=None)
    parsed.read(staged, encoding="utf-8")
    assert parsed["Document1"]["DocumentPath"] == "SCH\\Top.SchDoc"
    assert parsed["Document2"]["DocumentPath"] == "Documentation.OutJob"
    remove_stage(staged)
    assert not staged.parent.exists()


def test_rejects_output_outside_export_root(tmp_path, monkeypatch):
    monkeypatch.setenv("EDA_AGENT_SCHEMATIC_PDF_ROOT", str(tmp_path / "screens"))
    with pytest.raises(ValueError):
        checked_output_path(str(tmp_path / "elsewhere.pdf"))


def test_rejects_a_noncolor_outjob_before_staging(tmp_path, monkeypatch):
    source = tmp_path / "source" / "Sample.PrjPcb"
    source.parent.mkdir()
    (source.parent / "Top.SchDoc").write_bytes(b"schematic")
    source.write_text("[Document1]\nDocumentPath=Top.SchDoc\n", encoding="utf-8")
    root = tmp_path / "screens"
    monkeypatch.setenv("EDA_AGENT_SCHEMATIC_PDF_ROOT", str(root))
    mono = tmp_path / "mono.OutJob"
    mono.write_text("PageOptions1=Record=PageOptions|PrintKind=1|\n", encoding="utf-8")
    monkeypatch.setattr("eda_agent.tools.schematic_pdf.TEMPLATE", mono)
    with pytest.raises(ValueError, match="Color"):
        stage_schematic_project(str(source), str(root / "result.pdf"))
    assert not (root / "_pdf_stage").exists()


def test_variant_stage_preserves_project_definition_and_selects_output(tmp_path, monkeypatch):
    source = tmp_path / "source" / "Sample.PrjPcb"
    source.parent.mkdir()
    (source.parent / "Top.SchDoc").write_bytes(b"schematic")
    source.write_text(
        "[Design]\nVersion=1.0\n"
        "[Document1]\nDocumentPath=Top.SchDoc\n"
        "[Variant1]\nName=NoJ10\n",
        encoding="utf-8",
    )
    root = tmp_path / "screens"
    monkeypatch.setenv("EDA_AGENT_SCHEMATIC_PDF_ROOT", str(root))
    staged, _, _, _ = stage_schematic_project(
        str(source), str(root / "result.pdf"), "NoJ10")
    project = ConfigParser(interpolation=None)
    project.read(staged, encoding="utf-8")
    assert project["Variant1"]["Name"] == "NoJ10"
    job = (staged.parent / "Documentation.OutJob").read_text(encoding="utf-8")
    assert "VariantName=NoJ10" in job
    assert "OutputVariantName1=NoJ10" in job
    remove_stage(staged)
