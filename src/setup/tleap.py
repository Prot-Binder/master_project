from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple
import math
import re
import shutil

from src.utils.adjust_files import adjust_template_file
from src.utils.bash_run import run


@dataclass(frozen=True)
class TLeapPaths:
    template_tleap: Path               # templates/tleap.in.tpl
    ff_leaprc_cyclic: Path              # forcefield/leaprc.cyclic.ff14SB


def _bond_line_from_cfg(bond: Optional[str]) -> str:
    if not bond:
        return ""  # omit line

    b = bond.strip()
    if "-" in b:
        left, right = b.split("-", 1)
    else:
        parts = b.split()
        if len(parts) != 2:
            raise ValueError(f"system.bond has unexpected format: {bond!r}")
        left, right = parts

    return f"bond mol.{left.strip()} mol.{right.strip()}"


def _extract_volume_from_leap_log(leap_log: Path) -> float:
    """
    Parses 'Volume: <num> A^3' from leap.log and returns volume in A^3.
    """
    if not leap_log.exists():
        raise FileNotFoundError(f"Expected {leap_log} to exist after tleap run.")

    pattern = re.compile(r"Volume:\s*([\d.]+)\s*A\^3")
    for line in leap_log.read_text().splitlines():
        m = pattern.search(line)
        if m:
            return float(m.group(1))

    raise ValueError(f"Could not find a 'Volume: ... A^3' line in {leap_log}.")


def _compute_ion_count(volume_a3: float, factor: float = 0.00009) -> int:
    """
    Your current rule: ceil(volume * 0.00009)
    """
    return int(math.ceil(volume_a3 * factor))


def run_tleap(
    *,
    cluster: str,
    setup_dir: Path,
    pdb_path: Path,
    bond: Optional[str],
    paths: TLeapPaths,
) -> Tuple[Path, Path, int]:
    """
    Two-stage tleap:
      1) Run stage1 without ions to get leap.log volume
      2) Compute ions
      3) Run final tleap with ions

    Returns (final_prmtop, final_rst, n_ions_each)
    """

    pdb_path = pdb_path.resolve()

    # Copy FF resource(s) into setup_dir so this run is self-contained
    ff_dir = setup_dir / "ff"
    ff_dir.mkdir(exist_ok=True)
    shutil.copy2(paths.ff_leaprc_cyclic, ff_dir / "leaprc.cyclic.ff14SB")

    # ---------- Stage 1: no ions (get volume) ----------
    stage1_in = setup_dir / "tleap1.in"
    adjust_template_file(
        paths.template_tleap,
        stage1_in,
        {
            "FORCEFIELD_DIR": str(ff_dir),
            "PDB_PATH": str(pdb_path),
            "BOND": _bond_line_from_cfg(bond),
            "N_NA": 0,
            "N_CL": 0,
            "IN": 0,
        },
    )

    run(["tleap", "-f", stage1_in.name], cwd=setup_dir)

    leap_log = setup_dir / "leap.log"
    volume = _extract_volume_from_leap_log(leap_log)
    n_each = _compute_ion_count(volume)  # Na and Cl

    # ---------- Stage 2: final with ions ----------
    final_in = setup_dir / "tleap2.in"
    adjust_template_file(
        paths.template_tleap,
        final_in,
        {
            "FORCEFIELD_DIR": str(ff_dir),
            "PDB_PATH": str(pdb_path),
            "BOND": _bond_line_from_cfg(bond),
            "N_NA": n_each,
            "N_CL": n_each,
            "IN": 1,
        },
    )

    run(["tleap", "-f", final_in.name], cwd=setup_dir)

    prmtop = setup_dir / "system.prmtop"
    rst = setup_dir / "system.rst"

    if not prmtop.exists() or not rst.exists():
        raise RuntimeError(
            f"Final tleap did not generate expected outputs in {setup_dir}. "
            f"Missing {prmtop.name} or {rst.name}. Check {leap_log} / stdout."
        )

    return prmtop, rst, n_each
