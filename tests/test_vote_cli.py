# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 George Saliba <george.saliba@salitronic.com>
"""The public vote command reaches the existing layout comparison UI."""

from __future__ import annotations

import sys
from pathlib import Path

from eda_agent import server
from eda_agent.web import server as vote_web


def test_vote_command_loads_plan_and_starts_local_ui(monkeypatch, tmp_path):
    plan = Path(__file__).parent / "integration" / "fixtures" / "buck_5v_1a_plan.json"
    symbols = tmp_path / "symbols.json"
    symbols.write_text("[]", encoding="utf-8")
    seen = {}

    class App:
        def run(self, **kwargs):
            seen["run"] = kwargs

    def make_app(loaded_plan, extractor, plan_name):
        seen["plan"] = loaded_plan
        seen["name"] = plan_name
        return App()

    monkeypatch.setattr(vote_web, "create_app", make_app)
    monkeypatch.setattr(vote_web, "_count_records", lambda path: 0)
    monkeypatch.setattr(vote_web, "_pref_log_path", lambda: tmp_path / "votes.jsonl")
    monkeypatch.setattr(sys, "argv", [
        "eda-agent", "vote", "--plan", str(plan), "--symbols", str(symbols),
        "--port", "8767",
    ])

    assert server.main() == 0
    assert seen["name"] == "buck_5v_1a_plan"
    assert seen["plan"].parts
    assert seen["run"] == {
        "host": "127.0.0.1", "port": 8767, "debug": False,
        "use_reloader": False,
    }
