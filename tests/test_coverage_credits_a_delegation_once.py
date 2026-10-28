# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 George Saliba <george.saliba@salitronic.com>
"""A delegated chain is reachable for one object type, not for all of them.

GetSchProperty hands component reads to a generated routine behind
`If Obj.ObjectId = eSchComponent`. Counting those names for every
schematic type moved the coverage report from 29.7% to 46.5% on a
change that added thirty component properties, and credited a pin with
DescriptionString, which a pin cannot answer.

The report is the number this project steers by, so an overstatement in
it is worse than no report.
"""

from __future__ import annotations

import pytest

from eda_agent.sdk import coverage as cov

PASCAL = """
Function ReadThingGenerated(Obj : ISch_Thing; PropName : String;
    Var Found : Boolean) : String;
Begin
    Result := '';
    If PropName = 'OnlyOnThing' Then Result := Obj.OnlyOnThing
    Else If PropName = 'AlsoOnThing' Then Result := Obj.AlsoOnThing
    Else Exit;
    Found := True;
End;

Function GetSchProperty(Obj : ISch_GraphicalObject; PropName : String) : String;
Begin
    Result := '';
    If PropName = 'Shared' Then Result := Obj.Shared
    Else If Obj.ObjectId = eSchThing Then
    Begin
        Result := ReadThingGenerated(Obj, PropName, Have);
    End;
End;
"""


@pytest.fixture
def pascal(monkeypatch):
    monkeypatch.setattr(cov, "_read", lambda _rel: PASCAL)


def test_the_chain_reports_only_what_it_carries_itself(pascal):
    """Planning depends on this.

    If handled_names counted the delegated names, the generator would
    treat them as already handled and emit nothing, leaving the
    delegation calling a chain that no longer carried them.
    """
    assert cov.handled_names("GetSchProperty") == {"Shared"}


def test_delegated_names_are_keyed_by_the_type_that_guards_them(pascal):
    assert cov.delegated_names("GetSchProperty") == {
        "eSchThing": {"OnlyOnThing", "AlsoOnThing"}}


def test_a_type_the_guard_excludes_is_not_credited(pascal):
    delegated = cov.delegated_heads("GetSchProperty")
    assert delegated.get("eSchPin") is None
    assert "OnlyOnThing" not in cov.handled_heads("GetSchProperty")


def test_typed_extra_reader_does_not_credit_its_other_type_branches(monkeypatch):
    source = """
Function SchGetExtra(Obj : ISch_GraphicalObject; PropName : String) : String;
Begin
    If Obj.ObjectId = ePin Then
    Begin
        If PropName = 'DefaultValue' Then Result := Pin.DefaultValue;
    End
    Else If Obj.ObjectId = ePort Then
    Begin
        If PropName = 'AutoSize' Then Result := Port.AutoSize;
    End
    Else
    Begin
        Comp := Obj;
        If PropName = 'AliasAsText' Then Result := Comp.AliasAsText;
    End;
End;

Function GetSchProperty(Obj : ISch_GraphicalObject; PropName : String) : String;
Begin
    If SchExtraOwner(PropName) > 0 Then Result := SchGetExtra(Obj, PropName);
End;
"""
    monkeypatch.setattr(cov, "_read", lambda _rel: source)
    assert cov.typed_extra_heads("GetSchProperty") == {
        "ePin": {"DefaultValue"}, "ePort": {"AutoSize"},
        "eSchComponent": {"AliasAsText"},
    }
    assert "AliasAsText" not in cov.reachable_heads("GetSchProperty", "ePin")


def test_live_proven_pin_getters_are_scoped_to_pins():
    delegated = cov.delegated_heads("GetSchProperty")
    assert {"DescriptionString", "IdentifierString", "Handle"} <= delegated["ePin"]
    assert "IdentifierString" not in delegated.get("ePort", set())


