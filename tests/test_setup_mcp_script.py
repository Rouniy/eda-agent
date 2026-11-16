# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 George Saliba <george.saliba@salitronic.com>
"""The fork's Claude MCP setup helper preserves unrelated client settings."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.skipif(os.name != "nt" or not shutil.which("powershell.exe"),
                    reason="Windows PowerShell required")
def test_setup_mcp_cli_dry_run_add_and_remove(tmp_path: Path) -> None:
    script = Path(__file__).resolve().parents[1] / "scripts" / "setup-mcp.ps1"
    config = tmp_path / "claude.json"
    original = {"preserve": {"value": 42},
                "mcpServers": {"other": {"command": "other.exe"}}}
    config.write_text(json.dumps(original), encoding="utf-8")
    base = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", str(script), "-CliOnly", "-CliConfigPath", str(config),
            "-Command", sys.executable, "-Name", "altium", "-Yes"]

    subprocess.run(base + ["-DryRun"], check=True, capture_output=True,
                   text=True, timeout=20)
    assert json.loads(config.read_text(encoding="utf-8")) == original

    subprocess.run(base, check=True, capture_output=True, text=True,
                   timeout=20)
    raw = config.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf")
    added = json.loads(raw)
    assert added["preserve"] == original["preserve"]
    assert added["mcpServers"]["other"] == original["mcpServers"]["other"]
    assert added["mcpServers"]["altium"]["command"] == sys.executable

    subprocess.run(base + ["-Remove"], check=True, capture_output=True,
                   text=True, timeout=20)
    removed = json.loads(config.read_text(encoding="utf-8"))
    assert removed == original
    assert list(tmp_path.glob("claude.json.bak-setup-mcp-*"))
