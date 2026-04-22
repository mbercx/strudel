"""Unit tests for the vasprun.xml parser helpers."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

from strudel.outputs.parsers.vasprun import (
    VasprunXMLParser,
    _coerce_value,
    _convert_element,
    _parse_array,
    _parse_i,
    _parse_v,
    _parse_varray,
)


# ── _coerce_value ──


@pytest.mark.parametrize(
    ("text", "expected", "expected_type"),
    [
        ("42", 42, int),
        ("3.14", 3.14, float),
        ("1.5E+02", 150.0, float),
        ("hello", "hello", str),
        ("", "", str),
    ],
    ids=["int", "float", "scientific", "string", "empty"],
)
def test_coerce_value(text, expected, expected_type):
    """Each input is coerced to the narrowest numeric type, or left as str."""
    result = _coerce_value(text)
    if isinstance(expected, float):
        assert result == pytest.approx(expected)
    else:
        assert result == expected
    assert isinstance(result, expected_type)


# ── _parse_i ──


@pytest.mark.parametrize(
    ("xml", "expected_name", "expected_value"),
    [
        ('<i name="ISPIN">2</i>', "ISPIN", 2),
        ('<i name="ENCUT">400.0</i>', "ENCUT", pytest.approx(400.0)),
        ('<i name="NBANDS" type="int">128</i>', "NBANDS", 128),
        ('<i name="LWAVE" type="logical">T</i>', "LWAVE", True),
        ('<i name="LCHARG" type="logical">  F  </i>', "LCHARG", False),
        ('<i name="PREC" type="string"> accurate </i>', "PREC", "accurate"),
        ('<i type="int">5</i>', None, 5),
    ],
    ids=[
        "default-int",
        "default-float",
        "typed-int",
        "logical-true",
        "logical-false",
        "string",
        "missing-name",
    ],
)
def test_parse_i(xml, expected_name, expected_value):
    """Each type attribute dispatches correctly: default coercion, int, logical, string."""
    name, value = _parse_i(ET.fromstring(xml))
    assert name == expected_name
    assert value == expected_value


def test_parse_i_int_overflow():
    """Overflow '******' with type=int falls back to string."""
    name, value = _parse_i(ET.fromstring('<i name="NSTEP" type="int">******</i>'))
    assert name == "NSTEP"
    assert value == "******"
    assert isinstance(value, str)


def test_parse_i_default_coercion_overflow():
    """Overflow stars without type attr fall back to string via default coercion.

    Real pattern from overflow.xml: `<i name="e_fr_energy">****************</i>`.
    """
    name, value = _parse_i(ET.fromstring('<i name="e_fr_energy">****************</i>'))
    assert name == "e_fr_energy"
    assert value == "****************"
    assert isinstance(value, str)


# ── _parse_v ──


@pytest.mark.parametrize(
    ("xml", "expected_name", "expected_value"),
    [
        ('<v name="basis">  1.0  2.0  3.0 </v>', "basis", [1.0, 2.0, 3.0]),
        ("<v>0.0 0.0 0.0</v>", None, [0.0, 0.0, 0.0]),
        ("<v></v>", None, []),
    ],
    ids=["float-vector", "missing-name", "empty"],
)
def test_parse_v(xml, expected_name, expected_value):
    """Float vectors are parsed; missing name returns None; empty text returns []."""
    name, value = _parse_v(ET.fromstring(xml))
    assert name == expected_name
    assert value == pytest.approx(expected_value)


def test_parse_v_int_vector():
    """Integer vector with type=int returns ints, not floats."""
    name, value = _parse_v(ET.fromstring('<v name="kpoint" type="int">4 4 4</v>'))
    assert name == "kpoint"
    assert value == [4, 4, 4]
    assert all(isinstance(x, int) for x in value)


# ── _parse_varray ──


def test_parse_varray_matrix():
    """Parse a 2x3 varray."""
    xml = """
    <varray name="basis">
        <v>1.0 0.0 0.0</v>
        <v>0.0 2.0 0.0</v>
    </varray>
    """
    elem = ET.fromstring(xml)
    name, rows = _parse_varray(elem)
    assert name == "basis"
    assert len(rows) == 2
    assert rows[0] == pytest.approx([1.0, 0.0, 0.0])
    assert rows[1] == pytest.approx([0.0, 2.0, 0.0])


def test_parse_varray_unnamed():
    """Unnamed varray returns None for name."""
    xml = """
    <varray>
        <v>1.0 2.0 3.0</v>
    </varray>
    """
    elem = ET.fromstring(xml)
    name, rows = _parse_varray(elem)
    assert name is None
    assert rows == [pytest.approx([1.0, 2.0, 3.0])]


# ── _parse_array ──


def test_parse_array_flat_r_rows():
    """Array with flat <r> rows returns list of float lists."""
    xml = """
    <array name="dos">
        <field>energy</field>
        <field>total</field>
        <set>
            <r>  -10.0  0.5 </r>
            <r>   -9.0  1.0 </r>
        </set>
    </array>
    """
    elem = ET.fromstring(xml)
    result = _parse_array(elem)
    assert result["fields"] == ["energy", "total"]
    assert len(result["data"]) == 2
    assert result["data"][0] == pytest.approx([-10.0, 0.5])


def test_parse_array_rc_rows():
    """Array with <rc> rows coerces each cell individually."""
    xml = """
    <array>
        <field>element</field>
        <field>mass</field>
        <set>
            <rc><c>Si</c><c>28.085</c></rc>
            <rc><c>O</c><c>15.999</c></rc>
        </set>
    </array>
    """
    elem = ET.fromstring(xml)
    result = _parse_array(elem)
    assert result["data"][0] == ["Si", pytest.approx(28.085)]
    assert result["data"][1] == ["O", pytest.approx(15.999)]


def test_parse_array_named_sets():
    """Named sets with comment attributes become dict keys."""
    xml = """
    <array name="projected">
        <field>s</field>
        <set>
            <set comment="spin1">
                <set comment="kpoint1">
                    <r>0.1 0.2</r>
                </set>
            </set>
        </set>
    </array>
    """
    elem = ET.fromstring(xml)
    result = _parse_array(elem)
    assert "spin1" in result["data"]
    assert "kpoint1" in result["data"]["spin1"]
    assert result["data"]["spin1"]["kpoint1"][0] == pytest.approx([0.1, 0.2])


def test_parse_array_unnamed_sets():
    """Unnamed nested sets fall back to list."""
    xml = """
    <array>
        <field>val</field>
        <set>
            <set>
                <r>1.0</r>
            </set>
            <set>
                <r>2.0</r>
            </set>
        </set>
    </array>
    """
    elem = ET.fromstring(xml)
    result = _parse_array(elem)
    assert isinstance(result["data"], list)
    assert result["data"][0] == [pytest.approx([1.0])]
    assert result["data"][1] == [pytest.approx([2.0])]


def test_parse_array_no_set():
    """Array without a <set> element returns empty data."""
    xml = """
    <array>
        <field>x</field>
    </array>
    """
    elem = ET.fromstring(xml)
    result = _parse_array(elem)
    assert result["data"] == []


# ── _convert_element ──


def test_convert_element_i_dispatch():
    """<i> children are assembled into dict by name."""
    xml = """
    <root>
        <i name="ENCUT">400.0</i>
        <i name="ISPIN" type="int">2</i>
    </root>
    """
    result = _convert_element(ET.fromstring(xml))
    assert result["ENCUT"] == pytest.approx(400.0)
    assert result["ISPIN"] == 2


def test_convert_element_separator():
    """<separator> creates a named sub-dict."""
    xml = """
    <root>
        <separator name="electronic">
            <i name="ENCUT">300</i>
        </separator>
    </root>
    """
    result = _convert_element(ET.fromstring(xml))
    assert result["electronic"]["ENCUT"] == 300


def test_convert_element_array_named():
    """Named <array> is stored under its name."""
    xml = """
    <root>
        <array name="atoms">
            <field>element</field>
            <set><r>1.0</r></set>
        </array>
    </root>
    """
    result = _convert_element(ET.fromstring(xml))
    assert result["atoms"]["fields"] == ["element"]
    assert result["atoms"]["data"] == [pytest.approx([1.0])]


def test_convert_element_array_unnamed():
    """Unnamed <array> is appended to no_name_arrays list."""
    xml = """
    <root>
        <array>
            <field>x</field>
            <set><r>1.0</r></set>
        </array>
    </root>
    """
    result = _convert_element(ET.fromstring(xml))
    assert "no_name_arrays" in result
    assert len(result["no_name_arrays"]) == 1


def test_convert_element_time():
    """<time> is parsed as {cpu, wall} dict."""
    xml = """
    <root>
        <time name="totalsc">  1.23  4.56 </time>
    </root>
    """
    result = _convert_element(ET.fromstring(xml))
    assert result["totalsc"] == {
        "cpu": pytest.approx(1.23),
        "wall": pytest.approx(4.56),
    }


def test_convert_element_scstep():
    """<scstep> elements accumulate into a list."""
    xml = """
    <root>
        <scstep><i name="e_fr_energy">-1.0</i></scstep>
        <scstep><i name="e_fr_energy">-2.0</i></scstep>
    </root>
    """
    result = _convert_element(ET.fromstring(xml))
    assert len(result["scstep"]) == 2
    assert result["scstep"][0]["e_fr_energy"] == pytest.approx(-1.0)


def test_convert_element_calculation():
    """<calculation> elements accumulate into a list."""
    xml = """
    <root>
        <calculation><i name="step" type="int">1</i></calculation>
        <calculation><i name="step" type="int">2</i></calculation>
    </root>
    """
    result = _convert_element(ET.fromstring(xml))
    assert len(result["calculation"]) == 2
    assert result["calculation"][0]["step"] == 1


def test_convert_element_structure_unnamed():
    """<structure> without name stores under 'structure'."""
    xml = """
    <root>
        <structure>
            <i name="volume">50.0</i>
        </structure>
    </root>
    """
    result = _convert_element(ET.fromstring(xml))
    assert result["structure"]["volume"] == pytest.approx(50.0)


def test_convert_element_container_tags():
    """Container tags (crystal, energy, dos) are recursed."""
    xml = """
    <root>
        <energy>
            <i name="e_fr_energy">-5.0</i>
        </energy>
    </root>
    """
    result = _convert_element(ET.fromstring(xml))
    assert result["energy"]["e_fr_energy"] == pytest.approx(-5.0)


def test_convert_element_unknown_with_children():
    """Unknown tag with children is recursed and stored by name or tag."""
    xml = """
    <root>
        <parameters name="incar">
            <i name="ALGO" type="string">Normal</i>
        </parameters>
    </root>
    """
    result = _convert_element(ET.fromstring(xml))
    assert result["incar"]["ALGO"] == "Normal"


def test_convert_element_unknown_text_only():
    """Unknown tag with only text is coerced."""
    xml = """
    <root>
        <generator>42</generator>
    </root>
    """
    result = _convert_element(ET.fromstring(xml))
    assert result["generator"] == 42


def test_convert_element_field_dimension_skipped():
    """<field> and <dimension> tags are silently skipped."""
    xml = """
    <root>
        <field>energy</field>
        <dimension>1</dimension>
        <i name="keep">1</i>
    </root>
    """
    result = _convert_element(ET.fromstring(xml))
    assert "field" not in result
    assert "dimension" not in result
    assert result["keep"] == 1


def test_convert_element_i_without_name_skipped():
    """<i> without name is not added to the dict."""
    xml = """
    <root>
        <i type="int">99</i>
    </root>
    """
    result = _convert_element(ET.fromstring(xml))
    assert result == {}


# ── VasprunXMLParser ──


def test_vasprun_parser_full():
    """VasprunXMLParser.parse converts a minimal vasprun.xml document."""
    xml = """<?xml version="1.0"?>
    <modeling>
        <generator>
            <i name="program" type="string"> vasp </i>
        </generator>
        <incar>
            <i name="ENCUT">400.0</i>
            <i name="ISPIN" type="int">2</i>
        </incar>
    </modeling>
    """
    result = VasprunXMLParser.parse(xml)
    assert result["generator"]["program"] == "vasp"
    assert result["incar"]["ENCUT"] == pytest.approx(400.0)
    assert result["incar"]["ISPIN"] == 2
