import shutil
from dataclasses import fields
from pathlib import Path

import numpy as np
# TODO: change the way the directory paths are passed / created in this file


def _interval_windows(start: float, end: float, step: float) -> list[float]:
    windows = []
    for window in np.arange(start, end + step, step):
        windows.append(float(f"{float(window):.2f}"))
    return windows

def copy_template_files(ctx, method: str, clean: bool = True) -> None:

    template_dir = ctx.paths["templates"].resolve() / method
    dest_dir = ctx.paths[method]["input"]

    if not template_dir.is_dir():
        raise FileNotFoundError(f"Source dir not found: {template_dir}")

    # Start clean (optional, but avoids mixed old/new files)
    if clean and dest_dir.exists():
        shutil.rmtree(dest_dir)

    # TODO: check if creating directory here is useful
    dest_dir.mkdir(parents=True, exist_ok=True)

    for item in template_dir.iterdir():
        if item.is_file():
            shutil.copy2(item, dest_dir)
    print(f"[{method}] copied templates {template_dir} -> {dest_dir}")


def generate_eq(cfg, ctx) -> None:

    # path definitions
    eq_input_dir = ctx.paths["eq"]["input"]
    input_path = ctx.paths["eq"]["input"]
    output_path = ctx.paths["eq"]["pmd"]

    # copy template files from templates to results
    copy_template_files(ctx, method="eq")

    # copy restraint and coordinate files into correct folders
    setup_dir = ctx.paths["eq"]["setup"].resolve()
    shutil.copy2(setup_dir / "_lroa.r", eq_input_dir)
    shutil.copy2(setup_dir / "system.rst", eq_input_dir / "inpcrd0")
    shutil.copy2(setup_dir / "system.rst", eq_input_dir / "refc")

    # adjust input files for pull simulation
    mdin_file = eq_input_dir / "mdin4"
    mdin_text = (mdin_file.read_text()
                    .replace("{IN_PATH}", str(input_path))
                    .replace("{OUT_PATH}", str(output_path))
                    .replace("{NSTLIM}", str(cfg.methods.eq.nstlim)))
    mdin_output_file = eq_input_dir/f"mdin4"
    mdin_output_file.write_text(mdin_text)

def generate_pull(cfg, ctx):

    pull_input_dir = ctx.paths["pull"]["input"]

    # copy template files from template directory to pull directory
    copy_template_files(ctx, method="pull", clean=False)

    # copy restraint files from pull/setup to pull/input
    setup_dir = ctx.paths["pull"]["setup"].resolve()
    shutil.copy2(setup_dir / "pull.r", pull_input_dir)
    shutil.copy2(setup_dir / "_lroa.r", pull_input_dir)

    # define input path for restraints file
    input_path = ctx.paths["pull"]["input"]
    # define output path for amber output files
    output_path = ctx.paths["pull"]["pmd"]

    if cfg.methods.pull is None:
        raise ValueError("generate_pull requires cfg.methods.pull to be configured.")

    for interval in cfg.methods.pull.pull_intervals:
        w_start = float(f"{float(interval.start):.2f}")
        w_end = float(f"{float(interval.end):.2f}")
        step = float(f"{float(interval.step):.2f}")
        kappa = float(f"{float(interval.k):.2f}")

        # adjust input files for pull simulation
        mdin_file = pull_input_dir / "mdin5"
        restraint_file = pull_input_dir / "pull.r"
        windows = _interval_windows(w_start, w_end, step)
        for window_val in windows:
            window_str = f"{window_val:.2f}"
            mdin_text = (mdin_file.read_text()
                         .replace("{WINDOW}", str(window_str))
                         .replace("{IN_PATH}", str(input_path))
                         .replace("{OUT_PATH}", str(output_path))
                         .replace("{NSTLIM}", str(int(cfg.methods.pull.nstlim))))
            mdin_output_file = pull_input_dir/f"mdin5.w{window_str}"
            mdin_output_file.write_text(mdin_text)

            window_prev = float(f"{window_val - step:.2f}") if window_val - step >= w_start else window_val
            kappa_init = kappa / 2.0
            total_steps = int(cfg.methods.pull.nstlim)
            restraint_text = (restraint_file.read_text()
                              .replace("{WINDOW}", str(window_str))
                              .replace("{WINDOW_PREV}", str(window_prev))
                              .replace("{KAPPA}", str(kappa))
                              .replace("{KAPPA_INIT}", str(kappa_init))
                              .replace("{TOTAL_STEPS}", str(total_steps))
                              )
            restraint_output_file = pull_input_dir/f"pull{window_str}.r"
            restraint_output_file.write_text(restraint_text)

def generate_us(cfg, ctx):

    us_input_dir = ctx.paths["us"]["input"]

    # copy template files from template folder to results/input
    copy_template_files(ctx, method="us", clean=False)

    # copy restraint files from results/setup to results/input
    setup_dir = ctx.paths["us"]["setup"].resolve()
    shutil.copy2(setup_dir / "_lroaus.r", us_input_dir)

    # define input path for restraints file
    input_path = ctx.paths["us"]["input"]
    # define output path for amber output files
    output_path = ctx.paths["us"]["pmd"]

    if cfg.methods.us is None:
        raise ValueError("generate_us requires cfg.methods.us to be configured.")

    for interval in cfg.methods.us.us_intervals:
        w_start = float(f"{float(interval.start):.2f}")
        w_end = float(f"{float(interval.end):.2f}")
        step = float(f"{float(interval.step):.2f}")

        # adjust input files for us simulation
        mdin_file = us_input_dir / "mdin6"
        restraint_file = us_input_dir / "_lroaus.r"
        windows = _interval_windows(w_start, w_end, step)
        for window_val in windows:
            window_str = f"{window_val:.2f}"

            mdin_text = (mdin_file.read_text()
                    .replace("{WINDOW}", str(window_str))
                    .replace("{IN_PATH}", str(input_path))
                    .replace("{OUT_PATH}", str(output_path))
                    .replace("{NSTLIM}", str(int(cfg.methods.us.nstlim))))
            mdin_output_file = us_input_dir / f"mdin6.w{window_str}"
            mdin_output_file.write_text(mdin_text)

            restraint_text = (restraint_file.read_text()
                              .replace("{WINDOW}", str(window_str))
                              .replace("{KAPPA}", str(interval.k)))
            restraint_output_file = us_input_dir / f"_lroaus{window_str}.r"
            restraint_output_file.write_text(restraint_text)


def generate_rs_remd_eq(cfg, ctx):

    rs_remd_input_dir = ctx.paths["rs_remd"]["input"]

    copy_template_files(ctx, method="rs_remd")

    # copy restraint files from results/setup to results/input
    setup_dir = ctx.paths["rs_remd"]["setup"].resolve()
    shutil.copy2(setup_dir / "_lroa.r", rs_remd_input_dir)

    # define input path for restraints file
    input_path = ctx.paths["rs_remd"]["input"]
    # define output path for amber output files
    output_path = ctx.paths["rs_remd"]["eq"]

    if cfg.methods.rs_remd is None:
        raise ValueError("generate_us requires cfg.methods.rs_remd to be configured.")

    # adjust input files for us simulation
    mdin_file = rs_remd_input_dir / "eq"

    mdin_text = (mdin_file.read_text()
                 .replace("{NSTLIM}", str(cfg.methods.rs_remd.nstlim_eq))
                 .replace("{IN_PATH}", str(input_path))
                 .replace("{OUT_PATH}", str(output_path)))
    mdin_output_file = rs_remd_input_dir / "eq"
    mdin_output_file.write_text(mdin_text)

def generate_rs_remd_prod(cfg: dict, ctx):
    print("in generate rs_remd_prod")
    rs_remd_input_dir = ctx.paths["rs_remd"]["input"]

    # copy restraint files from results/setup to results/input
    setup_dir = ctx.paths["rs_remd"]["setup"].resolve()
    shutil.copy2(setup_dir / "_lroaus.r", rs_remd_input_dir)

    # define input path for restraints file
    input_path = "../input" # ctx.paths["rs_remd"]["input"]
    # define output path for amber output files
    output_path = "../run_output/pmd" # ctx.paths["rs_remd"]["pmd"].resolve() # "../run_output/pmd"  # ctx.paths["rs_remd"]["pmd"]

    if cfg.methods.rs_remd is None:
        raise ValueError("generate_us requires cfg.methods.rs_remd to be configured.")

    # adjust input files for us simulation
    mdin_file = rs_remd_input_dir / "mdin_rsremd"
    restraint_file = rs_remd_input_dir / "_lroaus.r"
    com_window = float(f"{ctx.com_distance:.2f}")

    # generate mdin files for each replica with correct number of steps and exchange frequency
    for rep in range(1,cfg.methods.rs_remd.n_rep+1):
        mdin_text = (mdin_file.read_text()
                     .replace("{NSTLIM}", str(cfg.methods.rs_remd.nstlim))
                     .replace("{NUMEXCHG}", str(cfg.methods.rs_remd.numexchg))
                     .replace("{IN_PATH}", str(input_path))
                     .replace("{OUT_PATH}", str(output_path))
                     .replace("{REPLICA}", str(rep)))
        mdin_output_file = rs_remd_input_dir / f"mdin_rsremd_rep{rep}"
        mdin_output_file.write_text(mdin_text)

    # generate rsremd group file
    lines = ["# RS-REMD groupfile (Hamiltonian Replica Exchange Molecular Dynamics)\n"]
    in_dir = ctx.paths["rs_remd"]["input"].resolve()
    out_dir = ctx.paths["rs_remd"]["amber"].resolve()
    top_dir = ctx.paths["rs_remd"]["top"].resolve()
    coord_init = str(ctx.paths["rs_remd"]["eq"] / "restrt_rsremd_eq")
    for rep in range(1, cfg.methods.rs_remd.n_rep+1):
        line = (
            f"-i {in_dir}/mdin_rsremd_rep{rep} "
            f"-c {coord_init} "
            f"-p {top_dir}/prmtop{rep} "
            f"-r {out_dir}/restrt_rs_rep{rep} "
            f"-o {out_dir}/mdout_rs_rep{rep} "
            f"-x {out_dir}/traj_rs_rep{rep}.nc "
            f"-inf {out_dir}/mdinfo_rs_rep{rep}\n"
        )
        lines.append(line)
    groupfile_path = rs_remd_input_dir / "rs_remd.groupfile"
    groupfile_path.write_text("".join(lines))

    # adjust _lroaus.r file for rs_remd production run
    restraint_text = (restraint_file.read_text()
                      .replace("{WINDOW}", str(f"{com_window:.2f}"))
                      .replace("{KAPPA}", str(cfg.methods.rs_remd.k)))
    restraint_output_file = rs_remd_input_dir / f"_lroaus_rs.r"
    restraint_output_file.write_text(restraint_text)


def generate_us_remd(cfg, ctx):
    us_remd_input_dir = ctx.paths["us_remd"]["input"]

    copy_template_files(ctx, method="us_remd", clean=False)

    setup_dir = ctx.paths["us_remd"]["setup"].resolve()
    shutil.copy2(setup_dir / "_lroaus.r", us_remd_input_dir)

    input_path = "../input"
    output_path = "../run_output/pmd"

    if cfg.methods.us_remd is None:
        raise ValueError("generate_us_remd requires cfg.methods.us_remd to be configured.")

    mdin_template = us_remd_input_dir / "mdin_usremd"
    restraint_template = us_remd_input_dir / "_lroaus.r"
    input_dir_rel = ctx.paths['us_remd']['input'] # "./input"
    top_dir_rel = ctx.paths['us_remd']['top']# "./top"
    amber_dir_rel = ctx.paths['us_remd']['amber']# "./run_output/amber"
    pull_amber_dir_rel = ctx.paths['pull']['amber']# "../pull/run_output/amber"

    for block_idx, interval in enumerate(cfg.methods.us_remd.us_remd_intervals):
        windows = _interval_windows(interval.start, interval.end, interval.step)
        groupfile_lines = [
            "# Example US-REMD groupfile\n",
            "# Replace the exact line structure in generate_us_remd() when needed.\n",
        ]

        for window in windows:
            window_str = f"{window:.2f}"

            mdin_text = (
                mdin_template.read_text()
                .replace("{NSTLIM}", str(cfg.methods.us_remd.nstlim))
                .replace("{NUMEXCHG}", str(cfg.methods.us_remd.numexchg))
                .replace("{IN_PATH}", input_path)
                .replace("{OUT_PATH}", output_path)
                .replace("{WINDOW}", window_str)
            )
            mdin_output_file = us_remd_input_dir / f"mdin_usremd_w{window_str}"
            mdin_output_file.write_text(mdin_text)
            kappa = str(cfg.methods.us_remd.us_remd_intervals[block_idx].k)
            restraint_text = (
                restraint_template.read_text()
                .replace("{WINDOW}", window_str)
                .replace("{KAPPA}", kappa)
            )
            restraint_output_file = us_remd_input_dir / f"_lroaus_usremd_w{window_str}.r"
            restraint_output_file.write_text(restraint_text)

            groupfile_lines.append(
                f"-i {input_dir_rel}/mdin_usremd_w{window_str} "
                f"-c {pull_amber_dir_rel}/restrt5.w{window_str} "
                f"-p {top_dir_rel}/prmtop1 "
                f"-r {amber_dir_rel}/restrt_usremd_b{block_idx}_rep{window_str} "
                f"-o {amber_dir_rel}/mdout_usremd_b{block_idx}_rep{window_str} "
                f"-x {amber_dir_rel}/traj_usremd_b{block_idx}_rep{window_str}.nc "
                f"-inf {amber_dir_rel}/mdinfo_usremd_b{block_idx}_rep{window_str}\n"
            )

        groupfile_path = us_remd_input_dir / f"us_remd_block{block_idx}.groupfile"
        groupfile_path.write_text("".join(groupfile_lines))


def generate_inputs(method: str, cfg: dict, ctx) -> None:
    if method == "eq":
        generate_eq(cfg, ctx)
    elif method == "pull":
        generate_pull(cfg, ctx)
    elif method == "us":
        generate_us(cfg, ctx)
    elif method == "rs_remd":
        generate_rs_remd_eq(cfg, ctx)
    elif method == "us_remd":
        generate_us_remd(cfg, ctx)
    else:
        raise ValueError(f"Unknown method: {method}")
