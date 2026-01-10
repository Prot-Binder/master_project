#!/usr/bin/env python3

import argparse

def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument("-m", "--mode", type=str, required=True, help="Select to generate file for equilibration (eq), replica exchange (remd) or both (all).")
    parser.add_argument("-r", "--replicas", nargs="+", type=int, required=True, help="Bash list as replicas. Use ${list[@]} for inline argument")
    parser.add_argument("-o", "--out", type=str, required=True, help="Specify output path for the replica exchange simulation")
    parser.add_argument("-t", "--top", type=str, required=True, help="Specify path to topology files with different LJ scaling.")
    return parser.parse_args()

"""
Generate groupfiles for (1) equilibration and (2) RS-REMD.
Adjust paths and filenames to match your setup.
"""

# ---- USER SETTINGS ----
# up to this point, the following filenames are fixed and connot be changed

mdin_equil = "mdin_remd_pre"   # same for all
mdin_rsremd = "mdin_rsremd"    # same for all
mdin_rsremd1 = "mdin_rsremd_res"    # same for all
mdin_rsremd2 = "mdin_rsremd_res2"    # same for all
ref_file   = "refc0"           # if you use refc
coord_init = "inpcrd4"         # starting coords for equil

H_REMD_METHOD = 3              # check your Amber version!

# -----------------------


def make_groupfile_equil(replicas, outdir, topdir, fname="eq.groupfile"):
    lines = ["# EQUILIBRATION groupfile (no REMD)\n"]
    for rep in replicas:
        line = (
            f"-O -i {mdin_equil} -ref {ref_file} -c {coord_init} "
            f"-p {topdir}/prmtop{rep} "
            f"-r {outdir}/inpcrd_rep{rep} "
            f"-o {outdir}/mdout_eqrs_rep{rep} "
            f"-x {outdir}/traj_eqrs_rep{rep}.nc "
            f"-inf {outdir}/mdinfo_rs_rep{rep}\n"
        )
        lines.append(line)
    with open(outdir + "/" + fname, "w") as f:
        f.writelines(lines)
    print(f"Wrote {fname}")


def make_groupfile_usre(us_windows, outdir, topdir, fname="usremd.groupfile"):
    lines = ["# RS-REMD groupfile (Hamiltonian REMD)\n"]
    for window in us_windows:
        line = (
            f"-O -rem {H_REMD_METHOD} "
            f"-i mdin_usre.rep{window} -ref {ref_file} "
            f"-c ./rep0_5h5r_res0/_run_output/restrt5.rep{window} "
            f"-p {topdir}/prmtop0 "
            f"-r {outdir}/restrt_usre_rep{window} "
            f"-o {outdir}/mdout_usre_rep{window} "
            f"-x {outdir}/traj_usre_rep{window}.nc "
            f"-inf {outdir}/mdinfo_usre_rep{window}\n"
        )
        lines.append(line)
    with open(outdir + "/" + fname, "w") as f:
        f.writelines(lines)
    print(f"Wrote {fname}")


if __name__ == "__main__":
    args = parse_args()
        
    if args.mode == "eq":
        make_groupfile_equil(args.replicas, args.out, args.top)
    elif args.mode == "remd":
        make_groupfile_usre(args.replicas, args.out, args.top)
    elif args.mode == "all":
        make_groupfile_equil(args.replicas, args.out, args.top)
        make_groupfile_rsremd(args.replicas, args.out, args.top)
    else:
        raise ValueError("Selected mode is invalid. Please select one of the following: eq, remd or all!")
