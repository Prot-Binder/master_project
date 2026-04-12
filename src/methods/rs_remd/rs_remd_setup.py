import subprocess
from pathlib import Path
import numpy as np

from src.setup.generate_input_files import generate_rs_remd_prod


def calculate_com_distance(ctx, cfg) -> float:
    receptor_start = cfg.protein_residues.split("-")[0]
    receptor_end = cfg.protein_residues.split("-")[1]

    ligand_start = cfg.ligand_residues.split("-")[0]
    ligand_end = cfg.ligand_residues.split("-")[1]

    highest_replica_scaling = cfg.methods.rs_remd.nrep
    top_path = str(ctx.paths["rs_remd"]["top"] / f"prmtop{highest_replica_scaling}")
    output_path = ctx.paths["rs_remd"]["root"] / "run_output"
    output_file = f"{output_path}/com_distance_{cfg.system.name}.dat"

    # trajectory is
    traj_path = str(ctx.paths["rs_remd"]["eq"] / "traj_eq.nc")
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

    data = np.loadtxt(output_file, comments="#", usecols=1)

    # calculate average distance from last 50% of data
    avg_com_dist = np.mean(data[len(data)/ 2:])
    try:
        avg_com_dist = float(avg_com_dist)
    except (TypeError, ValueError):
        raise TypeError(f"Average COM distance is not a float: {avg_com_dist!r}")

    if not np.isfinite(avg_com_dist):
        raise ValueError(f"Average COM distance is not finite: {avg_com_dist}. Check trajectory and topology files.")
    return avg_com_dist

def setup_rs_remd(cfg, ctx):
    # calculate com distance from eq trajectory and store in ctx for use in generating mdin files for us simulations
    avg_com_dist = calculate_com_distance(ctx, cfg)
    ctx.com_distance = avg_com_dist

    # generate input files for rs_remd after calculating com distance
    generate_rs_remd_prod(cfg, ctx)