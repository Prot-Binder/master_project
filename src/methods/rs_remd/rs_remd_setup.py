import subprocess
from pathlib import Path
import numpy as np

from src.config import resolve_rs_remd_eq_replica
from src.setup.generate_input_files import generate_rs_remd_prod


def calculate_com_distance(ctx, cfg) -> float:
    receptor_start = cfg.system.protein_residues.split("-")[0]
    receptor_end = cfg.system.protein_residues.split("-")[1]

    ligand_start = cfg.system.ligand_residues.split("-")[0]
    ligand_end = cfg.system.ligand_residues.split("-")[1]

    eq_replica = resolve_rs_remd_eq_replica(cfg)
    top_path = str(ctx.paths["rs_remd"]["top"] / f"prmtop{eq_replica}")
    output_path = ctx.paths["rs_remd"]["root"] / "run_output"
    output_file = f"{output_path}/com_distance_{cfg.system.name}.dat"

    # trajectory is
    traj_path = str(ctx.paths["rs_remd"]["eq"] / "traj_rsremd_eq.nc")
    cpptraj_in = f"""
    parm {top_path}
    trajin {traj_path}
    autoimage
    distance comdist :{receptor_start}-{receptor_end} :{ligand_start}-{ligand_end} out {output_file}
    run
    """

    cpptraj_file = ctx.paths["rs_remd"]["input"] / "comdist.in"
    Path(cpptraj_file).write_text(cpptraj_in)
    subprocess.run(["cpptraj", "-i", str(cpptraj_file)], check=True)

    data = np.atleast_1d(np.loadtxt(output_file, comments="#", usecols=1))
    idx = len(data) // 2 if len(data) > 2 else 0
    avg_com_dist = np.mean(data[idx:])

    try:
        avg_com_dist = float(avg_com_dist)
    except (TypeError, ValueError):
        raise TypeError(f"Average COM distance is not a float: {avg_com_dist!r}")

    if not np.isfinite(avg_com_dist):
        raise ValueError(f"Average COM distance is not finite: {avg_com_dist}. Check trajectory and topology files.")
    return avg_com_dist

def setup_rs_remd(cfg, ctx):
    restart_enabled = (
        cfg.methods.rs_remd is not None
        and cfg.methods.rs_remd.restart is not None
        and cfg.methods.rs_remd.restart.enabled
    )

    if not restart_enabled:
        # calculate com distance from eq trajectory and store in ctx for use in generating mdin files for us simulations
        avg_com_dist = calculate_com_distance(ctx, cfg)
        ctx.com_distance = avg_com_dist

    # generate input files for rs_remd after calculating com distance
    generate_rs_remd_prod(cfg, ctx)
