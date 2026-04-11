import shutil
from dataclasses import fields
from pathlib import Path

import numpy as np
# TODO: change the way the directory paths are passed / created in this file


def _configured_method_names(cfg) -> list[str]:
    method_names = []
    for method_field in fields(cfg.methods):
        method_cfg = getattr(cfg.methods, method_field.name)
        if method_cfg is not None:
            method_names.append(method_field.name)
    return method_names

def copy_files(root_dir: Path, dest_dir: Path) -> None:
    if not root_dir.is_dir():
        raise FileNotFoundError(f"Source dir not found: {root_dir}")

    # Start clean (optional, but avoids mixed old/new files)
    if dest_dir.exists():
        shutil.rmtree(dest_dir)

    # TODO: check if creating directory here is useful
    dest_dir.mkdir(parents=True, exist_ok=True)

    for item in root_dir.iterdir():
        if item.is_file():
            shutil.copy2(item, dest_dir)

def generate_eq(cfg, ctx) -> None:

    # path definitions
    template_dir = ctx.paths["templates"].resolve() / "eq"
    eq_input_dir = ctx.paths["eq"]["input"]
    input_path = ctx.paths["eq"]["input"]
    output_path = ctx.paths["eq"]["pmd"]

    # copy template files from templates to results
    copy_files(template_dir, eq_input_dir)
    print(f"[EQ] copied templates {template_dir} -> {eq_input_dir}")

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

    template_dir = ctx.paths["templates"].resolve() / "pull"
    pull_dir = ctx.paths["pull"]["input"]

    # copy template files from template directory to pull directory
    copy_files(template_dir, pull_dir)
    print(f"[PULL] copied templates {template_dir} -> {pull_dir}")

    # copy restraint files from pull/setup to pull/input
    setup_dir = ctx.paths["pull"]["setup"].resolve()
    shutil.copy2(setup_dir / "pull.r", pull_dir)
    shutil.copy2(setup_dir / "_lroa.r", pull_dir)

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
        mdin_file = pull_dir / "mdin5"
        restraint_file = pull_dir / "pull.r"
        for window in np.arange(w_start, w_end + step, step):
            window_val = float(f"{float(window):.2f}")
            window_str = f"{window_val:.2f}"
            mdin_text = (mdin_file.read_text()
                         .replace("{WINDOW}", str(window_str))
                         .replace("{IN_PATH}", str(input_path))
                         .replace("{OUT_PATH}", str(output_path))
                         .replace("{NSTLIM}", str(int(cfg.methods.pull.nstlim))))
            mdin_output_file = pull_dir/f"mdin5.w{window_str}"
            mdin_output_file.write_text(mdin_text)

            window_prev = float(f"{window - step:.2f}") if window - step >= w_start else window_val
            kappa_init = kappa / 2.0
            total_steps = float(cfg.methods.pull.nstlim)
            restraint_text = (restraint_file.read_text()
                              .replace("{WINDOW}", str(window_str))
                              .replace("{WINDOW_PREV}", str(window_prev))
                              .replace("{KAPPA}", str(kappa))
                              .replace("{KAPPA_INIT}", str(kappa_init))
                              .replace("{TOTAL_STEPS}", str(total_steps))
                              )
            restraint_output_file = pull_dir/f"pull{window_str}.r"
            restraint_output_file.write_text(restraint_text)

def generate_us(cfg, ctx):
    # copy template files from template folder to results/input
    templates_root: Path = ctx.paths["templates"].resolve()
    template_dir = templates_root / "us"
    dest_dir = ctx.paths["us"]["input"]

    copy_files(template_dir, dest_dir)

    print(f"[US] copied templates {template_dir} -> {dest_dir}")

    # copy restraint files from results/setup to results/input
    setup_dir = ctx.paths["us"]["setup"].resolve()
    shutil.copy2(setup_dir / "_lroaus.r", dest_dir)

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
        mdin_file = dest_dir / "mdin6"
        restraint_file = dest_dir / "_lroaus.r"
        for window in np.arange(w_start, w_end + step, step):
            window_val = float(f"{float(window):.2f}")
            window_str = f"{window_val:.2f}"

            mdin_text = (mdin_file.read_text()
                    .replace("{WINDOW}", str(window_str))
                    .replace("{IN_PATH}", str(input_path))
                    .replace("{OUT_PATH}", str(output_path)))
            mdin_output_file = dest_dir / f"mdin6.w{window_str}"
            mdin_output_file.write_text(mdin_text)

            restraint_text = (restraint_file.read_text()
                              .replace("{WINDOW}", str(window_str))
                              .replace("{KAPPA}", str(interval.k)))
            restraint_output_file = dest_dir / f"_lroaus{window_str}.r"
            restraint_output_file.write_text(restraint_text)


def generate_rs_remd(method: str, cfg: dict):
    pass


def generate_us_remd(method: str, cfg: dict):
    pass


def generate_inputs(method: str, cfg: dict, ctx) -> None:
    if method == "eq":
        generate_eq(cfg, ctx)
    elif method == "pull":
        generate_pull(cfg, ctx)
    elif method == "us":
        generate_us(cfg, ctx)
    elif method == "rs_remd":
        pass
        generate_rs_remd(cfg, ctx)
    elif method == "us_remd":
        pass
        generate_us_remd(cfg, ctx)
    else:
        raise ValueError(f"Unknown method: {method}")
