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


@pytest.mark.asyncio
async def test_run_drc_reports_truncation_and_fresh_totals(tmp_path, monkeypatch):
    report = tmp_path / "drc_batch_check.html"
    report.write_text('''
<td class="DRC_summary_header_col1">Rule Violations:</td>
<td class="DRC_summary_header_col2"></td><td class="DRC_summary_header_col3">125</td>
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
    assert result["violations_returned"] == 100
    assert result["violations_truncated"] is True
