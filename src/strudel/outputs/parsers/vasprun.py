"""Generic vasprun.xml parser."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

from dough.outputs.parsers.base import BaseOutputFileParser


def _coerce_value(text: str) -> int | float | str:
    """Coerce a string to int, float, or leave as string."""
    try:
        return int(text)
    except ValueError:
        try:
            return float(text)
        except ValueError:
            return text


def _parse_i(elem: ET.Element) -> tuple[str | None, Any]:
    """Parse an ``<i>`` scalar element, applying the type attribute."""
    name = elem.get("name")
    text = (elem.text or "").strip()
    type_attr = elem.get("type", "")

    if type_attr == "logical":
        value: Any = text.upper().startswith("T")
    elif type_attr == "string":
        value = text
    else:
        # `_coerce_value` also handles the "******" overflow case by falling back to str.
        value = _coerce_value(text)

    return name, value


def _parse_v(elem: ET.Element) -> tuple[str | None, list[int] | list[float]]:
    """Parse a ``<v>`` vector element into a list of floats."""
    name = elem.get("name")
    text = (elem.text or "").strip()

    type_attr = elem.get("type", "")
    if type_attr == "int":
        return name, [int(x) for x in text.split()]
    return name, [float(x) for x in text.split()]


def _parse_varray(
    elem: ET.Element,
) -> tuple[str | None, list[list[int] | list[float]]]:
    """Parse a ``<varray>`` into a list of vectors."""
    name = elem.get("name")
    rows = [_parse_v(v)[1] for v in elem.findall("v")]
    return name, rows


def _parse_set(set_elem: ET.Element) -> Any:
    """Parse a ``<set>`` element from an ``<array>``.

    Leaf sets (containing ``<r>`` / ``<rc>`` rows) return a list of rows.
    Nested sets with ``comment`` attributes return a dict keyed by comment.
    Nested sets without comments return a list.
    """
    child_sets = set_elem.findall("set")

    if not child_sets:
        rows: list[Any] = []
        for child in set_elem:
            if child.tag == "r":
                text = (child.text or "").strip()
                rows.append([float(x) for x in text.split()])
            elif child.tag == "rc":
                rows.append(
                    [_coerce_value((c.text or "").strip()) for c in child.findall("c")]
                )
        return rows

    use_dict = any(s.get("comment") for s in child_sets)
    if use_dict:
        return {s.get("comment"): _parse_set(s) for s in child_sets}
    return [_parse_set(s) for s in child_sets]


def _parse_array(elem: ET.Element) -> dict[str, Any]:
    """Parse an ``<array>`` element into a dict with fields and data.

    Returns a dict with ``"fields"`` (column names) and ``"data"`` (nested lists).
    Named sets get their ``comment`` attribute as key; unnamed sets produce lists.
    """
    fields = [f.text.strip() if f.text else "" for f in elem.findall("field")]
    top_set = elem.find("set")
    data = _parse_set(top_set) if top_set is not None else []
    return {"fields": fields, "data": data}


_CONTAINER_TAGS = frozenset(
    (
        "crystal",
        "energy",
        "dos",
        "eigenvalues",
        "projected",
        "total",
        "partial",
    )
)

_LIST_TAGS = frozenset(("scstep", "calculation"))

_SKIP_TAGS = frozenset(("dimension", "field"))


def _convert_element(elem: ET.Element) -> dict[str, Any]:
    """Recursively convert an XML element into a nested dict.

    Dispatches on the vasprun.xml tag vocabulary:

    - ``<i>``: typed scalar
    - ``<v>``: float vector
    - ``<varray>``: 2D array
    - ``<separator>`` / ``<structure>``: named grouping (recurse, store by name)
    - ``<array>``: tabular data with fields + set hierarchy
    - ``<time>``: two floats (cpu, wall)
    - ``<scstep>`` / ``<calculation>``: accumulate into a list
    - ``<crystal>``, ``<energy>``, ``<dos>``, etc.: generic containers (recurse, store by tag)
    """
    result: dict[str, Any] = {}

    for child in elem:
        tag = child.tag

        if tag == "i":
            name, value = _parse_i(child)
            if name:
                result[name] = value

        elif tag == "v":
            name, value = _parse_v(child)
            if name:
                result[name] = value

        elif tag == "varray":
            name, value = _parse_varray(child)
            if name:
                result[name] = value

        elif tag in ("separator", "structure"):
            name = child.get("name") or tag
            result[name] = _convert_element(child)

        elif tag == "array":
            name = child.get("name")
            if name:
                result[name] = _parse_array(child)
            else:
                result.setdefault("no_name_arrays", []).append(_parse_array(child))

        elif tag == "time":
            name = child.get("name")
            text = (child.text or "").strip()
            values = [float(x) for x in text.split()]
            if name and len(values) == 2:
                result[name] = {"cpu": values[0], "wall": values[1]}

        elif tag in _LIST_TAGS:
            result.setdefault(tag, []).append(_convert_element(child))

        elif tag in _CONTAINER_TAGS:
            result[tag] = _convert_element(child)

        elif tag in _SKIP_TAGS:
            pass

        else:
            name = child.get("name")
            parsed_child = _convert_element(child)
            if parsed_child:
                result[name or tag] = parsed_child
            elif not list(child) and child.text and child.text.strip():
                result[tag] = _coerce_value(child.text.strip())

    return result


class VasprunXMLParser(BaseOutputFileParser):
    """Parse vasprun.xml into a nested Python dict.

    Converts the full XML tree generically — no output-specific logic.
    The resulting dict mirrors the XML structure and can be queried with ``glom``.
    """

    @staticmethod
    def parse(content: str) -> dict[str, Any]:
        root = ET.fromstring(content)
        return _convert_element(root)
