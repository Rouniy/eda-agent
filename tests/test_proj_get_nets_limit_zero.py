# SPDX-License-Identifier: Apache-2.0
"""proj_get_nets with limit 0 returns every pin, as limit 0 does in obj_query.

It used to return nothing: the handler compared the count with the limit
before the first pin, so 0 >= 0 stopped the walk at once and the reply was
an empty list marked truncated.
"""
from pathlib import Path

from tests.pascal_source import load

PROJECT = Path(__file__).resolve().parents[1] / "scripts" / "altium" / "Project.pas"


def test_zero_means_no_limit():
    body = load(PROJECT)["Proj_GetNets"]
    assert "Unlimited := (Limit <= 0);" in body
    assert "If (Not Unlimited) And (Count >= Limit) Then" in body
    assert "If Count >= Limit Then" not in body
    assert "Unlimited : Boolean" in body or "LimitHit, Unlimited : Boolean" in body
