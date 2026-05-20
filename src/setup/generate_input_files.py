import shutil
from dataclasses import fields
from pathlib import Path

import numpy as np
from src.config import (
    resolve_continuation_restart_file,
    resolve_rs_remd_restart_file,
    resolve_rs_remd_restart_restraint_file,
    us_remd_interval_window_kappas,
    us_remd_interval_windows,
)
from src.setup.restraint_cases import (
    build_restraint_case_name,
    format_restraint_kappa_token,
    rendered_restraint_filename,
    rendered_restraint_mdin_filename,
)
# TODO: change the way the directory paths are passed / created in this file


def _interval_windows(start: float, end: float, step: float) -> list[float]:
    windows = []
    for window in np.arange(start, end + step, step):
        windows.append(float(f"{float(window):.2f}"))
    return windows

def _render_template_text(text: str, values: dict[str, object]) -> str:
    rendered = text
    for key, value in values.items():
        rendered = rendered.replace("{" + key + "}", str(value))
    return rendered


def _restraint_equilibration_filename(target_class: str) -> str:
    if target_class == "complex":
        return "_lroa.r"
    if target_class == "ligand":
        return "_lB.r"
    if target_class == "receptor":
        return "_rB.r"
    raise ValueError(f"Unsupported restraint target class: {target_class}")


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


def generate_restraint_contribution_inputs(cfg, ctx) -> None:
    if cfg.restraints is None or len(cfg.restraints.contributions) == 0:
        return

    seen_classes: set[str] = set()
    for contribution in cfg.restraints.contributions:
        target_class = contribution.target_class
        if target_class in seen_classes:
            continue
        seen_classes.add(target_class)

        class_setup_dir = ctx.paths["restraints"]["setup"][target_class].resolve()
        class_eq_paths = ctx.paths["restraints"]["eq"][target_class]
        class_input_dir = class_eq_paths["input"].resolve()
        class_output_dir = class_eq_paths["pmd"].resolve()
        class_input_dir.mkdir(parents=True, exist_ok=True)
        class_output_dir.mkdir(parents=True, exist_ok=True)

        class_restraint_name = _restraint_equilibration_filename(target_class)
        source_class_restraint = class_setup_dir / class_restraint_name
        if not source_class_restraint.is_file():
            raise FileNotFoundError(
                f"Source class restraint file for '{target_class}' not found: {source_class_restraint}"
            )

        rendered_class_restraint = class_input_dir / source_class_restraint.name
        shutil.copy2(source_class_restraint, rendered_class_restraint)

        class_template_dir = ctx.paths["templates"].resolve() / "restraints" / target_class
        if not class_template_dir.is_dir():
            raise FileNotFoundError(
                f"Class restraint template directory not found for '{target_class}': {class_template_dir}"
            )

        class_templates = sorted(path for path in class_template_dir.iterdir() if path.is_file())
        if len(class_templates) == 0:
            raise FileNotFoundError(
                f"No class equilibration templates found for '{target_class}' in {class_template_dir}"
            )

        for class_template in class_templates:
            rendered_class_template = class_input_dir / class_template.name
            rendered_class_text = _render_template_text(
                class_template.read_text(),
                {
                    "RESTRAINT_PATH": str(rendered_class_restraint.resolve()),
                    "OUTPUT_PATH": str(class_output_dir),
                    "CASE_INDEX": target_class,
                },
            )
            rendered_class_template.write_text(rendered_class_text)

    for contribution in cfg.restraints.contributions:
        class_setup_dir = ctx.paths["restraints"]["setup"][contribution.target_class].resolve()
        contribution_paths = ctx.paths["restraints"]["contributions"][contribution.name]
        contribution_input_dir = contribution_paths["input"].resolve()
        contribution_output_dir = contribution_paths["pmd"].resolve()
        contribution_input_dir.mkdir(parents=True, exist_ok=True)
        contribution_output_dir.mkdir(parents=True, exist_ok=True)

        source_restraint_file = class_setup_dir / contribution.restraint_file
        if not source_restraint_file.is_file():
            raise FileNotFoundError(
                f"Source restraint file for contribution '{contribution.name}' not found: {source_restraint_file}"
            )

        template_dir = ctx.paths["templates"].resolve() / "restraints" / contribution.name
        if not template_dir.is_dir():
            raise FileNotFoundError(
                f"Template directory for restraint contribution '{contribution.name}' not found: {template_dir}"
            )

        mdin_templates = sorted(path for path in template_dir.iterdir() if path.is_file())
        if len(mdin_templates) == 0:
            raise FileNotFoundError(
                f"No mdin template files found for restraint contribution '{contribution.name}' in {template_dir}"
            )

        source_restraint_text = source_restraint_file.read_text()
        for kappa in contribution.kappa:
            kappa_token = format_restraint_kappa_token(kappa)
            case_index = build_restraint_case_name(contribution.name, kappa)
            rendered_restraint_name = rendered_restraint_filename(source_restraint_file.name, kappa)
            rendered_restraint_path = contribution_input_dir / rendered_restraint_name
            rendered_restraint_text = _render_template_text(
                source_restraint_text,
                {
                    "KAPPA": kappa_token,
                },
            )
            rendered_restraint_path.write_text(rendered_restraint_text)

            for mdin_template in mdin_templates:
                rendered_mdin_name = rendered_restraint_mdin_filename(
                    mdin_template.name,
                    contribution.name,
                    kappa,
                )
                rendered_mdin_path = contribution_input_dir / rendered_mdin_name
                rendered_mdin_text = _render_template_text(
                    mdin_template.read_text(),
                    {
                        "NSTLIM": contribution.nstlim if contribution.nstlim is not None else "",
                        "RESTRAINT_PATH": str(rendered_restraint_path.resolve()),
                        "OUTPUT_PATH": str(contribution_output_dir),
                        "CASE_INDEX": case_index,
                    },
                )
                rendered_mdin_path.write_text(rendered_mdin_text)


def generate_eq(cfg, ctx) -> None:

    # path definitions
    eq_input_dir = ctx.paths["eq"]["input"]
    input_path = ctx.paths["eq"]["input"].resolve()
    output_path = ctx.paths["eq"]["pmd"].resolve()

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

    mdin_eq_file = eq_input_dir / "mdin_eq"
    if mdin_eq_file.exists() and cfg.methods.eq.nstlim_eq is not None:
        mdin_eq_text = (
            mdin_eq_file.read_text()
            .replace("{IN_PATH}", str(input_path))
            .replace("{OUT_PATH}", str(output_path))
            .replace("{NSTLIM}", str(cfg.methods.eq.nstlim_eq))
        )
        mdin_eq_file.write_text(mdin_eq_text)

def generate_pull(cfg, ctx):

    pull_input_dir = ctx.paths["pull"]["input"]

    # copy template files from template directory to pull directory
    copy_template_files(ctx, method="pull", clean=False)

    # copy restraint files from pull/setup to pull/input
    setup_dir = ctx.paths["pull"]["setup"].resolve()
    shutil.copy2(setup_dir / "pull.r", pull_input_dir)
    shutil.copy2(setup_dir / "_lroa.r", pull_input_dir)

    # define input path for restraints file
    input_path = "./input" # ctx.paths["pull"]["input"]
    # define output path for amber output files
    output_path = "./run_output/pmd" # ctx.paths["pull"]["pmd"]

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
    input_path = ctx.paths["us"]["input"].resolve()
    # define output path for amber output files
    output_path = ctx.paths["us"]["pmd"].resolve()

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
    input_path = ctx.paths["rs_remd"]["input"].resolve()
    # define output path for amber output files
    output_path = ctx.paths["rs_remd"]["eq"].resolve()

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
    input_path = "../input"
    # define output path for amber output files
    output_path = "../run_output/pmd"

    if cfg.methods.rs_remd is None:
        raise ValueError("generate_us requires cfg.methods.rs_remd to be configured.")

    # adjust input files for us simulation
    mdin_file = rs_remd_input_dir / "mdin_rsremd"
    mdin_eq_each_file = rs_remd_input_dir / "mdin_rsremd_eq_each"
    restraint_file = rs_remd_input_dir / "_lroaus.r"
    restart_enabled = (
        cfg.methods.rs_remd.restart is not None
        and cfg.methods.rs_remd.restart.enabled
    )
    com_window = None if restart_enabled else float(f"{ctx.com_distance:.2f}")

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

        if cfg.methods.rs_remd.nstlim_eq_each is not None:
            mdin_eq_each_text = (mdin_eq_each_file.read_text()
                                 .replace("{NSTLIM}", str(cfg.methods.rs_remd.nstlim_eq_each))
                                 .replace("{IN_PATH}", str(input_path))
                                 .replace("{OUT_PATH}", str(output_path))
                                 .replace("{REPLICA}", str(rep)))
            mdin_eq_each_output_file = rs_remd_input_dir / f"mdin_rsremd_eq_each_rep{rep}"
            mdin_eq_each_output_file.write_text(mdin_eq_each_text)

    # generate optional short equilibration group file for each replica/scaling
    in_dir = ctx.paths["rs_remd"]["input"].resolve()
    out_dir = ctx.paths["rs_remd"]["amber"].resolve()
    top_dir = ctx.paths["rs_remd"]["top"].resolve()
    coord_init = str((ctx.paths["rs_remd"]["eq"] / "restrt_rsremd_eq").resolve())

    if cfg.methods.rs_remd.nstlim_eq_each is not None and not restart_enabled:
        eq_each_lines = ["# RS-REMD short equilibration at each scaling\n"]
        for rep in range(1, cfg.methods.rs_remd.n_rep+1):
            eq_each_line = (
                f"-i {in_dir}/mdin_rsremd_eq_each_rep{rep} "
                f"-c {coord_init} "
                f"-p {top_dir}/prmtop{rep} "
                f"-r {out_dir}/restrt_rs_eq_each_rep{rep} "
                f"-o {out_dir}/mdout_rs_eq_each_rep{rep} "
                f"-x {out_dir}/traj_rs_eq_each_rep{rep}.nc "
                f"-inf {out_dir}/mdinfo_rs_eq_each_rep{rep}\n"
            )
            eq_each_lines.append(eq_each_line)
        eq_each_groupfile_path = rs_remd_input_dir / "rs_remd_eq_each.groupfile"
        eq_each_groupfile_path.write_text("".join(eq_each_lines))

    # generate rsremd production group file
    lines = ["# RS-REMD groupfile (Hamiltonian Replica Exchange Molecular Dynamics)\n"]
    for rep in range(1, cfg.methods.rs_remd.n_rep+1):
        if restart_enabled:
            coord_path = str(resolve_rs_remd_restart_file(cfg, rep).resolve())
        else:
            coord_path = (
                f"{out_dir}/restrt_rs_eq_each_rep{rep}"
                if cfg.methods.rs_remd.nstlim_eq_each is not None
                else coord_init
            )
        line = (
            f"-i {in_dir}/mdin_rsremd_rep{rep} "
            f"-c {coord_path} "
            f"-p {top_dir}/prmtop{rep} "
            f"-r {out_dir}/restrt_rs_rep{rep} "
            f"-o {out_dir}/mdout_rs_rep{rep} "
            f"-x {out_dir}/traj_rs_rep{rep}.nc "
            f"-inf {out_dir}/mdinfo_rs_rep{rep}\n"
        )
        lines.append(line)
    groupfile_path = rs_remd_input_dir / "rs_remd.groupfile"
    groupfile_path.write_text("".join(lines))

    restraint_output_file = rs_remd_input_dir / f"_lroaus_rs.r"
    if restart_enabled:
        shutil.copy2(resolve_rs_remd_restart_restraint_file(cfg), restraint_output_file)
    else:
        # adjust _lroaus.r file for rs_remd production run
        restraint_text = (restraint_file.read_text()
                          .replace("{WINDOW}", str(f"{com_window:.2f}"))
                          .replace("{KAPPA}", str(cfg.methods.rs_remd.k)))
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
    input_dir_rel = ctx.paths['us_remd']['input'].resolve()
    top_dir_rel = ctx.paths['us_remd']['top'].resolve()
    amber_dir_rel = ctx.paths['us_remd']['amber'].resolve()
    pull_amber_dir_rel = ctx.paths['pull']['amber'].resolve()

    for block_idx, interval in enumerate(cfg.methods.us_remd.us_remd_intervals):
        windows = us_remd_interval_windows(interval)
        window_kappas = dict(us_remd_interval_window_kappas(interval))
        groupfile_lines = [
            "# Example US-REMD groupfile\n",
            "# Replace the exact line structure in generate_us_remd() when needed.\n",
        ]

        for window in windows:
            window_str = f"{window:.2f}"
            if (
                cfg.methods.us_remd.continuation is not None
                and cfg.methods.us_remd.continuation.enabled
            ):
                coord_file = str(
                    resolve_continuation_restart_file(
                        cfg,
                        cfg.methods.us_remd.continuation,
                        current_method="us_remd",
                        window=window_str,
                    ).resolve()
                )
            else:
                coord_file = f"{pull_amber_dir_rel}/restrt5.w{window_str}"

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
            kappa = str(window_kappas[window])
            restraint_text = (
                restraint_template.read_text()
                .replace("{WINDOW}", window_str)
                .replace("{KAPPA}", kappa)
            )
            restraint_output_file = us_remd_input_dir / f"_lroaus_usremd_w{window_str}.r"
            restraint_output_file.write_text(restraint_text)

            groupfile_lines.append(
                f"-i {input_dir_rel}/mdin_usremd_w{window_str} "
                f"-c {coord_file} "
                f"-p {top_dir_rel}/prmtop1 "
                f"-r {amber_dir_rel}/restrt_usremd_b{block_idx}_rep{window_str} "
                f"-o {amber_dir_rel}/mdout_usremd_b{block_idx}_rep{window_str} "
                f"-x {amber_dir_rel}/traj_usremd_b{block_idx}_rep{window_str}.nc "
                f"-inf {amber_dir_rel}/mdinfo_usremd_b{block_idx}_rep{window_str}\n"
            )

        groupfile_path = us_remd_input_dir / f"us_remd_block{block_idx}.groupfile"
        groupfile_path.write_text("".join(groupfile_lines))


def generate_gauss_rank(cfg, ctx) -> None:
    if cfg.methods.gauss_rank is None:
        raise ValueError("generate_gauss_rank requires cfg.methods.gauss_rank to be configured.")

    method_cfg = cfg.methods.gauss_rank
    gauss_rank_input_dir = ctx.paths["gauss_rank"]["input"]
    gauss_rank_pmd_dir = ctx.paths["gauss_rank"]["pmd"].resolve()
    gauss_rank_setup_dir = ctx.paths["gauss_rank"]["setup"].resolve()

    copy_template_files(ctx, method="gauss_rank")

    mdin_template = gauss_rank_input_dir / "mdin"
    if not mdin_template.exists():
        raise FileNotFoundError(f"gauss_rank mdin template not found after copy: {mdin_template}")

    shutil.copy2(gauss_rank_setup_dir / "_lroaus.r", gauss_rank_input_dir)

    restraint_file = gauss_rank_input_dir / "_lroaus.r"
    if not restraint_file.exists():
        raise FileNotFoundError(f"gauss_rank restraint file not found after copy: {restraint_file}")

    mdin_template_text = mdin_template.read_text()
    for replicate_idx in range(method_cfg.n_reps):
        rendered_mdin_text = _render_template_text(
            mdin_template_text,
            {
                "REP": str(replicate_idx),
                "OUT_PATH": str(gauss_rank_pmd_dir),
                "IN_PATH": str(gauss_rank_input_dir.resolve()),
                "NSTLIM": str(method_cfg.nstlim),
            },
        )
        (gauss_rank_input_dir / f"mdin_rep{replicate_idx}").write_text(rendered_mdin_text)

    rendered_restraint_text = _render_template_text(
        restraint_file.read_text(),
        {
            "KAPPA": f"{float(method_cfg.kappa):.2f}",
            "WINDOW": "0.0",
        },
    )
    restraint_file.write_text(rendered_restraint_text)


def generate_inputs(method: str, cfg: dict, ctx) -> None:
    if method == "eq":
        generate_eq(cfg, ctx)
    elif method == "gauss_rank":
        generate_gauss_rank(cfg, ctx)
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
