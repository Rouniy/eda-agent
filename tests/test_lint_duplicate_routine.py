# SPDX-License-Identifier: Apache-2.0
"""A source merge cannot leave two DelphiScript routines with one name."""

from scripts.altium.lint import _scan_duplicate_routines


def test_duplicate_routine_is_a_build_error():
    lines = [
        "Function SaveOne(Path : String) : Boolean;",
        "Begin",
        "    Result := True;",
        "End;",
        "{ A later upstream definition with the same name. }",
        "Function SaveOne(Path : String) : Boolean;",
        "Begin",
        "    Result := False;",
        "End;",
    ]
    findings = _scan_duplicate_routines("Sample.pas", lines)
    assert [(item.rule, item.severity, item.line) for item in findings] == [
        ("duplicate-routine", "error", 6),
    ]
