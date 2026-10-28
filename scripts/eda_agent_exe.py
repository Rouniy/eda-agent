# SPDX-License-Identifier: Apache-2.0
"""PyInstaller entry point for the installed eda-agent package."""

from eda_agent.server import main


if __name__ == "__main__":
    raise SystemExit(main())
