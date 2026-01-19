from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.utils.adjust_files import adjust_template_file
from src.utils.bash_run import run


@dataclass(frozen=True)
class ParmEdPaths:
    template: Path   # templates/parmed/hmr.parmed.tpl


def run_hmr(
    *,
    setup_dir: Path,
    in_prmtop: Path,
    out_prmtop: Path,
    paths: ParmEdPaths,
) -> Path:
    """
    Apply hydrogen mass repartitioning (HMR) using ParmEd.

    Parameters
    ----------
    setup_dir : Path
        Directory where ParmEd will be executed.
    in_prmtop : Path
        Input topology (must exist).
    out_prmtop : Path
        Output topology (will be created).
    paths : ParmEdPaths
        Locations of ParmEd templates.

    Returns
    -------
    Path
        Path to the HMR-modified prmtop.
    """

    if not in_prmtop.exists():
        raise FileNotFoundError(f"Input prmtop not found: {in_prmtop}")

    parmed_in = setup_dir / "HMR.parmed"

    print("parmed_in: " + str(parmed_in))
    print("setup dir: " + str(setup_dir))

    # Adjust the ParmEd input file
    adjust_template_file(
        paths.template,
        parmed_in,
        {
            "IN_PRMTOP": in_prmtop.name,     # relative to setup_dir
            "OUT_PRMTOP": out_prmtop.name,
        },
    )

    # Run ParmEd inside setup_dir
    run(["parmed", "-i", parmed_in.name], cwd=setup_dir)

    # if not out_prmtop.exists():
    #     raise RuntimeError(
    #         f"HMR failed: expected output topology not found: {out_prmtop}"
    #     )

    return out_prmtop
