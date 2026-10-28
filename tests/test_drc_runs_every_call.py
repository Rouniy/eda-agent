# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 George Saliba <george.saliba@salitronic.com>
"""Every DRC call checks the board, and its report is found where AD25 puts it.

PCB:DesignRuleCheck acts on the CURRENT board. The first run opens its
report document, which takes the focus, so a second run in the same
session checked nothing and handed back the old report: a caller
re-running DRC to confirm a fix read a stale answer. And AD25 writes the
report into the project's output folder, so drc_confirmed was false on
every run there even when the check ran.
"""
from __future__ import annotations

from pathlib import Path

from tests.pascal_source import load

_PCB = Path(__file__).resolve().parents[1] / "scripts" / "altium" / "PCB.pas"


def _body():
    return load(_PCB)["PCB_RunDRC"]


def test_the_board_is_shown_before_the_check_runs():
    body = _body()
    assert body.index("Client.ShowDocument(BoardDoc)") < body.index(
        "RunProcess('PCB:DesignRuleCheck')")


def test_the_project_output_report_is_watched_too():
    body = _body()
    assert "DrcOutputsReportPath(Board)" in body
    before = body.index("OutputsBefore := DrcReportAge(OutputsPath)")
    after = body.index("OutputsAfter := DrcReportAge(OutputsPath)")
    run = body.index("RunProcess('PCB:DesignRuleCheck')")
    assert before < run < after
    # The reply names the file that changed.
    assert "ReportPath := OutputsPath" in body


def test_the_output_report_name_follows_altium():
    helper = load(_PCB)["DrcOutputsReportPath"]
    assert "'Design Rule Check - '" in helper
    assert "Project.DM_GetOutputPath" in helper


def test_ad25_default_output_paths_are_watched_for_freshness():
    body = _body()
    helper = load(_PCB)["DrcDefaultOutputsReportPath"]
    assert "'Project Outputs for '" in helper
    assert "ExtractFilePath(ProjPath)" in helper
    assert "ExtractFilePath(BoardPath)" in helper
    run = body.index("RunProcess('PCB:DesignRuleCheck')")
    for prefix in ("ProjectDefault", "BoardDefault"):
        assert body.index(f"{prefix}Before := DrcReportAge(") < run
        assert body.index(f"{prefix}After := DrcReportAge(") > run
        assert f"{prefix}After > {prefix}Before" in body


def test_modal_drc_advances_past_each_violation():
    body = _body()
    loop = body[body.index("Violation := Iterator.FirstPCBObject;"):]
    loop = loop[:loop.index("Board.BoardIterator_Destroy(Iterator);")]
    assert "Inc(ViolationCount);" in loop
    assert "JsonItems := JsonItems + BuildViolationJson(Violation);" in loop
    assert "Violation := Iterator.NextPCBObject;" in loop
    assert "ReportFresh := True;" not in loop
