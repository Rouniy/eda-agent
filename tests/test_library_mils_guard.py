# SPDX-License-Identifier: Apache-2.0
"""Shared library coordinate transport must not send invalid numbers."""

import pytest

from eda_agent.tools.library import _mils


def test_library_mils_keeps_decimal_precision_and_refuses_nonfinite_values():
    assert _mils(25) == "25"
    assert _mils(-1000.125) == "-1000.125"
    assert _mils(0.0001) == "0.0001"
    for bad in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(ValueError, match="finite"):
            _mils(bad)
