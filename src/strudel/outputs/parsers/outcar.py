"""OUTCAR parser for magnetization data."""

from __future__ import annotations

import re
from typing import Any

from dough.outputs.parsers.base import BaseOutputFileParser

_ORBITALS = ("s", "p", "d", "f")
_MAG_HEADER_RE = re.compile(r"magnetization \((\w)\)")


def _parse_magnetization_block(lines: list[str], start: int) -> list[dict[str, float]]:
    """Parse a ``magnetization (x/y/z)`` block starting after the header.

    Expects ``start`` to point at the ``# of ion ...`` header line.
    Returns a list of per-site dicts with orbital + ``"tot"`` keys.
    """
    sites: list[dict[str, float]] = []

    idx = start + 2
    while idx < len(lines):
        line = lines[idx].strip()
        if not line or line.startswith("-"):
            idx += 1
            continue
        if line.startswith("tot"):
            break

        parts = line.split()
        if len(parts) >= 2:
            try:
                int(parts[0])
            except ValueError:
                break

            values = [float(x) for x in parts[1:]]
            site: dict[str, float] = dict(zip(_ORBITALS, values[:-1]))
            site["tot"] = values[-1]
            sites.append(site)

        idx += 1

    return sites


class OutcarParser(BaseOutputFileParser):
    """Parse OUTCAR for magnetization and related quantities.

    Only the **last** ionic step's data is returned.
    """

    @staticmethod
    def parse(content: str) -> dict[str, Any]:
        lines = content.splitlines()
        result: dict[str, Any] = {"magnetization": {}}

        site_mag: dict[str, list[dict[str, float]]] = {}
        total_mag: float | None = None

        for idx, line in enumerate(lines):
            stripped = line.strip()

            match = _MAG_HEADER_RE.match(stripped)
            if match:
                direction = match.group(1)
                header_idx = idx + 1
                while header_idx < len(lines) and not lines[header_idx].strip():
                    header_idx += 1
                sites = _parse_magnetization_block(lines, header_idx)
                if sites:
                    site_mag[direction] = sites

            elif stripped.startswith("number of electron"):
                parts = stripped.split()
                if len(parts) >= 6 and parts[4] == "magnetization":
                    try:
                        total_mag = float(parts[5])
                    except ValueError:
                        pass

        if site_mag:
            result["magnetization"]["site_magnetization"] = site_mag
        if total_mag is not None:
            result["magnetization"]["total_magnetization"] = total_mag

        return result
