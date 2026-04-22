"""Data regression tests for VasprunXMLParser against real fixtures."""

from __future__ import annotations

import pytest

from strudel.outputs.parsers.vasprun import VasprunXMLParser


@pytest.mark.parametrize("case", ["basic", "magnetic"])
def test_vasprun_parser_regression(case, files_path, robust_data_regression_check):
    """Full parse of a real vasprun.xml fixture, checked against stored snapshot."""
    xml_path = files_path / "vasp" / case / "vasprun.xml"
    result = VasprunXMLParser.parse(xml_path.read_text())
    robust_data_regression_check(result)
