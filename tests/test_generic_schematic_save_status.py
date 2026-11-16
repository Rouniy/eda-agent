# SPDX-License-Identifier: Apache-2.0
"""A generic schematic edit marks the document dirty without saving it."""

from pathlib import Path

from tests.pascal_source import load


GENERIC = Path(__file__).resolve().parents[1] / "scripts" / "altium" / "Generic.pas"


def test_single_sheet_modify_reports_dirty_not_saved():
    functions = load(GENERIC, minimum=20)
    for name in ("ProcessActiveDoc", "ProcessDocByPath"):
        body = functions[name]
        assert "MarkDocDirtyByPath(DocPath);" in body
        assert "If IsMutating And ((TotalMatched > 0) Or (Mode = 'create')) Then" in body
        assert "Saved := True;" not in body
        assert '"modified":' in body
        assert "(TotalMatched > 0)" in body
