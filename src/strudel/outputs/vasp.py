"""VASP output class and output mapping."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any, TextIO

from dough.outputs.base import BaseOutput, output_mapping
from glom import Spec

from strudel.outputs.parsers.outcar import OutcarParser
from strudel.outputs.parsers.vasprun import VasprunXMLParser


@output_mapping
class _VaspMapping:
    # Read energies from the last scstep rather than the calculation-level <energy>
    # block: the latter folds in classical VDW corrections (when `LVDW`/`IVDW` is
    # set) and a PV term (when `PSTRESS` is set), so it does not cleanly equal the
    # converged SCF energy.
    total_energy: Annotated[
        float,
        Spec(
            (
                "vasprun.calculation",
                lambda c: c[-1]["scstep"][-1]["energy"]["e_fr_energy"],
            )
        ),
    ]
    """Total energy in eV (electronic free energy, TOTEN)."""

    energy_no_entropy: Annotated[
        float,
        Spec(
            (
                "vasprun.calculation",
                lambda c: c[-1]["scstep"][-1]["energy"]["e_wo_entrp"],
            )
        ),
    ]
    """Total energy without entropy in eV."""

    fermi_energy: Annotated[
        float,
        Spec(("vasprun.calculation", lambda c: c[-1]["dos"]["efermi"])),
    ]
    """Fermi energy in eV."""

    energy_cutoff: Annotated[float, Spec("vasprun.parameters.electronic.ENMAX")]
    """Plane-wave energy cutoff in eV."""

    n_scf_steps: Annotated[
        list[int],
        Spec(("vasprun.calculation", lambda c: [len(step["scstep"]) for step in c])),
    ]
    """Number of electronic SCF steps per ionic step."""

    structure: Annotated[
        dict[str, Any],
        Spec(
            {
                "symbols": ("vasprun.atominfo.atoms.data", [lambda row: row[0]]),
                "cell": "vasprun.finalpos.crystal.basis",
                "positions": "vasprun.finalpos.positions",
            }
        ),
    ]
    """Final structure with keys ``"symbols"`` (list[str]), ``"cell"`` (list[list[float]], Å), ``"positions"`` (list[list[float]], fractional)."""

    total_magnetization: Annotated[
        float, Spec("outcar.magnetization.total_magnetization")
    ]
    """Total cell magnetization in μ_B."""

    site_magnetization: Annotated[
        list[dict[str, float]], Spec("outcar.magnetization.site_magnetization.x")
    ]
    """Per-site magnetization (x-component) in μ_B, list of dicts with s/p/d/f/tot keys."""


class VaspOutput(BaseOutput[_VaspMapping]):
    """Output container for VASP calculations."""

    @classmethod
    def from_dir(cls, directory: str | Path) -> VaspOutput:
        """Construct from a VASP calculation directory.

        Looks for ``vasprun.xml`` and ``OUTCAR`` in the given directory.
        """
        directory = Path(directory)

        vasprun_file = directory / "vasprun.xml"
        outcar_file = directory / "OUTCAR"

        return cls.from_files(
            vasprun=vasprun_file if vasprun_file.exists() else None,
            outcar=outcar_file if outcar_file.exists() else None,
        )

    @classmethod
    def from_files(
        cls,
        *,
        vasprun: None | str | Path | TextIO = None,
        outcar: None | str | Path | TextIO = None,
    ) -> VaspOutput:
        """Construct from explicit file paths or handles."""

        raw_outputs: dict[str, Any] = {}

        if vasprun is not None:
            raw_outputs["vasprun"] = VasprunXMLParser.parse_from_file(vasprun)
        if outcar is not None:
            raw_outputs["outcar"] = OutcarParser.parse_from_file(outcar)

        return cls(raw_outputs=raw_outputs)
