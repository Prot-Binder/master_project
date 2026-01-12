import shutil
from pathlib import Path

from src.setup.calc_ions import output_file


def copy_files(root_dir: Path, dest_dir: Path) -> None:
    if not root_dir.is_dir():
        raise FileNotFoundError(f"Source dir not found: {root_dir}")

    # Start clean (optional, but avoids mixed old/new files)
    if dest_dir.exists():
        shutil.rmtree(dest_dir)

    dest_dir.mkdir(parents=True, exist_ok=True)

    for item in root_dir.iterdir():
        if item.is_file():
            shutil.copy2(item, dest_dir)

def generate_eq(method: str, cfg: dict) -> None:
    # copy files from templates to results
    templates_root: Path = cfg["paths"]["templates_root"]
    results_root: Path = cfg["paths"]["results_root"]
    system: str = cfg["system"]

    template_dir = templates_root / method
    dest_dir = results_root / system / method / "input"

    copy_files(template_dir, dest_dir)

    print(f"[{method}] copied templates {template_dir} -> {dest_dir}")

def generate_us(method: str, cfg: dict):
    # copy files from templates to results
    templates_root: Path = cfg["paths"]["templates_root"]
    results_root: Path = cfg["paths"]["results_root"]
    system: str = cfg["system"]
    tag: str = cfg["tag"]

    template_dir = templates_root / method
    dest_dir = results_root / system / method / tag / "input"

    copy_files(template_dir, dest_dir)

    print(f"[{method}] copied templates {template_dir} -> {dest_dir}")

    # adjust mdin5 and mdin6 files: adjust the restraints and the path for the output files
    # TODO: adjust the restrint file path and the output file path!
    mdin_file = dest_dir/"mdin5"
    for window in cfg.windows:
        text = mdin_file.read_text().replace("{WINDOW}", str(window))
        output_file = dest_dir/f"mdin5.rep{window}"
        output_file.write_text(text)

    mdin_file = dest_dir / "mdin6"
    for window in cfg.windows:
        text = mdin_file.read_text().replace("{WINDOW}", str(window))
        output_file = dest_dir / f"mdin6.rep{window}"
        output_file.write_text(text)


def generate_rs_remd(cfg: dict):
    pass


def generate_us_remd(cfg: dict):
    pass


def generate_inputs(method: str, cfg: dict) -> None:
    if method == "eq":
        generate_eq(cfg)
    elif method == "us":
        generate_us(cfg)
    elif method == "rs_remd":
        generate_rs_remd(cfg)
    elif method == "us_remd":
        generate_us_remd(cfg)
    else:
        raise ValueError(f"Unknown method: {method}")