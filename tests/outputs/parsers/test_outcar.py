"""Unit tests for the OUTCAR parser."""

from __future__ import annotations

from pathlib import Path

import pytest

from strudel.outputs.parsers.outcar import OutcarParser

FIXTURE = Path(__file__).parent.parent / "fixtures" / "vasp" / "magnetic" / "OUTCAR"


def test_parse_takes_last_total_magnetization():
    """VASP writes ``number of electron ... magnetization M`` per SCF step; take the last."""
    content = (
        "number of electron       8.0000000 magnetization       3.0000000\n"
        "number of electron       7.9999965 magnetization       2.7242808\n"
    )
    result = OutcarParser.parse(content)
    assert result["magnetization"]["total_magnetization"] == pytest.approx(2.7242808)


def test_parse_extracts_site_magnetization_x():
    """A ``magnetization (x)`` block becomes ``site_magnetization.x``."""
    content = (
        " magnetization (x)\n"
        "\n"
        "# of ion       s       p       d       tot\n"
        "------------------------------------------\n"
        "    1       -0.048  -0.030   2.972   2.894\n"
        "\n"
        "tot                -0.048  -0.030   2.972   2.894\n"
    )
    result = OutcarParser.parse(content)
    assert result["magnetization"]["site_magnetization"]["x"] == [
        {"s": -0.048, "p": -0.030, "d": 2.972, "tot": 2.894}
    ]


def test_parse_from_file_magnetic_fixture():
    """End-to-end: the trimmed Fe OUTCAR fixture yields the expected magnetization."""
    result = OutcarParser.parse_from_file(FIXTURE)

    mag = result["magnetization"]
    assert mag["total_magnetization"] == pytest.approx(2.7242808)
    assert mag["site_magnetization"]["x"] == [
        {"s": -0.048, "p": -0.030, "d": 2.972, "tot": 2.894}
    ]
