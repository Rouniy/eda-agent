# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 George Saliba <george.saliba@salitronic.com>
"""The activity log is read once per line as it grows. Reading a text
file with tell() inside a for loop raises; the error left the offset
behind and the same line was taken in again every poll, hundreds of
times."""
from __future__ import annotations

from eda_agent.web.dashboard import ActivityTailer


def _line(i: int) -> str:
    return (f"2026-11-05 14:55:{i:02d}.118,110,pcb.get_layout_model,OK,1344,"
            '{"success":true}\n')


def test_new_lines_are_read_once_each(tmp_path):
    log = tmp_path / "activity.log"
    log.write_text(_line(1), encoding="utf-8")
    tailer = ActivityTailer(log)
    offset = tailer.read_new(0)
    with open(log, "a", encoding="utf-8", newline="") as f:
        for i in range(2, 6):
            f.write(_line(i))
        f.write(_line(6)[:30])
    offset = tailer.read_new(offset)
    assert [e.timestamp for e in tailer.entries] == [
        f"2026-11-05 14:55:{i:02d}.118" for i in range(1, 6)]
    assert tailer.read_new(offset) == offset
    assert len(tailer.entries) == 5
    with open(log, "a", encoding="utf-8", newline="") as f:
        f.write(_line(6)[30:])
    offset = tailer.read_new(offset)
    assert tailer.read_new(offset) == offset
    assert [e.timestamp for e in tailer.entries][-1] == "2026-11-05 14:55:06.118"
    assert len(tailer.entries) == 6
