# SPDX-License-Identifier: Apache-2.0
"""Fresh DRC totals distinguish active and waived board violations."""

import pytest

from eda_agent.tools import pcb


def test_batch_report_counts_active_and_waived(tmp_path):
    report = tmp_path / "drc_batch_check.html"
    report.write_text('''
<td class="DRC_summary_header_col1">Warnings:</td>
<td class="DRC_summary_header_col2"></td><td class="DRC_summary_header_col3">0</td>
<td class="DRC_summary_header_col1">Rule Violations:</td>
<td class="DRC_summary_header_col2"></td><td class="DRC_summary_header_col3">0</td>
<td class="DRC_summary_header_col1">Waived Violations:</td>
<td class="DRC_summary_header_col2"></td>
<td class="DRC_summary_header_col3" style="color : red">1</td>
''', encoding="utf-8")
    assert pcb._drc_report_counts(str(report)) == {
        "warnings": 0, "rule_violations": 0, "waived_violations": 1}


def test_batch_report_retains_zero_rule_rows_and_validates_the_sum(tmp_path):
    report = tmp_path / "drc_batch_rules.html"
    report.write_text('''
<td class="DRC_summary_header_col1">Rule Violations:</td>
<td class="DRC_summary_header_col2"></td><td class="DRC_summary_header_col3">2</td>
<table><tr><th class="column1">Rule Violations</th><th class="column2">Count</th></tr>
<tr><td class="column1"><a href="#one">Clearance Constraint (All),(All)</a></td>
<td class="column2">2</td></tr>
<tr><td class="column1"><a href="#two">Short-Circuit Constraint (All),(All)</a></td>
<td class="column2">0</td></tr>
<tr><td class="column1">Total</td><td class="column2">2</td></tr></table>
''', encoding="utf-8")
    assert pcb._drc_report_rules(str(report)) == [
        {"label": "Clearance Constraint (All),(All)", "violations": 2},
        {"label": "Short-Circuit Constraint (All),(All)", "violations": 0},
    ]
    assert pcb._drc_report_rules(str(tmp_path / "missing.html")) is None


def test_batch_report_exposes_altiums_early_stop(tmp_path):
    report = tmp_path / "drc_batch_limited.html"
    report.write_text('''
<p class="error">ERROR : More than 500 violations detected, DRC was stopped</p>
''', encoding="utf-8")
    assert pcb._drc_report_stop_limit(str(report)) == 500


@pytest.mark.asyncio
async def test_run_drc_reports_truncation_and_fresh_totals(tmp_path, monkeypatch):
    report = tmp_path / "drc_batch_check.html"
    report.write_text('''
<td class="DRC_summary_header_col1">Rule Violations:</td>
<td class="DRC_summary_header_col2"></td><td class="DRC_summary_header_col3">125</td>
<table><tr><th class="column1">Rule Violations</th><th class="column2">Count</th></tr>
<tr><td class="column1">Clearance Constraint (All),(All)</td>
<td class="column2">125</td></tr>
<tr><td class="column1">Total</td><td class="column2">125</td></tr></table>
''', encoding="utf-8")

    class Bridge:
        async def send_command_async(self, command, params):
            assert command == "pcb.run_drc"
            return {"mode": "batch", "drc_confirmed": True,
                    "report_path": str(report), "violation_count": 125,
                    "violations": [{} for _ in range(100)]}

    class Mcp:
        def tool(self):
            def capture(fn):
                if fn.__name__ == "pcb_run_drc":
                    self.run_drc = fn
                return fn
            return capture

    monkeypatch.setattr(pcb, "get_bridge", Bridge)
    mcp = Mcp()
    pcb.register_pcb_tools(mcp)
    result = await mcp.run_drc()
    assert result["report_counts"] == {"rule_violations": 125}
    assert result["report_rules"] == [
        {"label": "Clearance Constraint (All),(All)", "violations": 125}]
    assert result["report_rule_count"] == 1
    assert result["report_rules_total_matches_header"] is True
    assert result["report_stopped_at_limit"] is False
    assert result["violations_returned"] == 100
    assert result["violations_truncated"] is True
