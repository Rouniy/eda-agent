# SPDX-License-Identifier: Apache-2.0
"""A crashed X2 must not leave app_attach permanently blocked."""

import os
from types import SimpleNamespace

from eda_agent.tools import application


def test_app_attach_ignores_progress_from_previous_altium(tmp_path, monkeypatch):
    marker = tmp_path / "progress_old.json"
    marker.write_text("{}")
    os.utime(marker, (100, 100))
    bridge = SimpleNamespace(process_manager=SimpleNamespace(get_altium_pid=lambda: 42))
    monkeypatch.setattr(application.psutil, "Process",
                        lambda pid: SimpleNamespace(create_time=lambda: 200))

    assert not application._current_altium_has_progress(bridge, tmp_path)
    os.utime(marker, (300, 300))
    assert application._current_altium_has_progress(bridge, tmp_path)
