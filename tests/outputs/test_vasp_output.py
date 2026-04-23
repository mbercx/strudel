"""Integration tests for the VaspOutput class."""

from __future__ import annotations

from pathlib import Path

import pytest

from strudel.outputs import VaspOutput

FIXTURES = Path(__file__).parent / "fixtures" / "vasp"


@pytest.mark.parametrize("fixture", ["basic", "magnetic"])
def test_from_dir(robust_data_regression_check, fixture):
    """End-to-end: ``VaspOutput.from_dir`` parses each fixture into the expected outputs."""
    vasp_out = VaspOutput.from_dir(FIXTURES / fixture)

    robust_data_regression_check({"base_outputs": vasp_out.get_output_dict()})


def test_magnetic_outputs():
    """The magnetic fixture surfaces both ``total_magnetization`` and ``site_magnetization``."""
    vasp_out = VaspOutput.from_dir(FIXTURES / "magnetic")

    available = vasp_out.list_outputs()
    assert "total_magnetization" in available
    assert "site_magnetization" in available

    assert vasp_out.outputs.total_magnetization == pytest.approx(2.7242808)
    assert vasp_out.outputs.site_magnetization == [
        {"s": -0.048, "p": -0.030, "d": 2.972, "tot": 2.894}
    ]


def test_basic_no_outcar_skips_magnetization():
    """The basic fixture has no OUTCAR; magnetization outputs are unavailable."""
    vasp_out = VaspOutput.from_dir(FIXTURES / "basic")

    available = vasp_out.list_outputs()
    assert "total_magnetization" not in available
    assert "site_magnetization" not in available
