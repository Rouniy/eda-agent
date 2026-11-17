# SPDX-License-Identifier: Apache-2.0
"""Two cycle-time fixes measured on a live board (2026-11-15).

* The keep-alive pings only when nothing reached Altium for a whole
  interval, from this server or any other (a shared stamp): 101 servers had
  sent 51,000 pings in three weeks against 5,700 real commands.
* pcb.batch_move_components runs the whole batch inside one edit: each part
  was its own PreProcess/PostProcess, about 190 ms a part.
"""
from __future__ import annotations

import os
import time
from pathlib import Path
from types import SimpleNamespace

from eda_agent.bridge.altium_bridge import AltiumBridge

from tests.pascal_source import load

_ALTIUM = Path(__file__).resolve().parents[1] / "scripts" / "altium"


def _bridge(workspace):
    b = object.__new__(AltiumBridge)
    b.config = SimpleNamespace(workspace_dir=workspace)
    return b


def test_a_ping_is_skipped_while_altium_was_reached_recently(tmp_path):
    b = _bridge(tmp_path)
    assert not b._keepalive_not_needed()          # nothing yet: ping
    b._note_keepalive("application.ping")
    assert not b._keepalive_not_needed()          # its own ping is the interval
    b._note_keepalive("pcb.get_components")
    assert b._keepalive_not_needed()              # a real command just reached it


def test_another_servers_answer_counts_too(tmp_path):
    other, mine = _bridge(tmp_path), _bridge(tmp_path)
    other._note_keepalive("application.ping")
    (tmp_path / AltiumBridge.KEEPALIVE_STAMP).write_text("1", encoding="ascii")  # another pid
    assert mine._keepalive_not_needed()
    stamp = tmp_path / AltiumBridge.KEEPALIVE_STAMP
    old = time.time() - AltiumBridge.KEEPALIVE_INTERVAL - 5
    os.utime(stamp, (old, old))
    assert not mine._keepalive_not_needed()       # stale: ping


def test_the_batch_move_is_one_edit():
    body = load(_ALTIUM / "PCB.pas")["PCB_BatchMoveComponents"]
    assert body.count("PcbBeginEdit(0)") == 1 and body.count("PcbEndEdit(0)") == 1
    outer = body.index("PcbBeginEdit(0)")
    loop = body.index("While Length(Remaining) > 0 Do")
    modify = body.index("PCBM_BeginModify", loop)
    close = body.index("PcbEndEdit(0)")
    nets = body.index("Board.AnalyzeNet(NetObj)")
    assert outer < loop < modify < close < nets
