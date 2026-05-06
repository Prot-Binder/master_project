import argparse

from src.config import load_config, inject_paths, prepare_directories, validate_equilibration_settings, copy_yaml_input, \
    compute_paths, validate_continuation_settings
from src.methods.JobContext import JobContext
from src.setup.system import setup_simulation
from src.setup.restraint_cases import group_restraint_cases_by_class
from src.utils.backup_manager import BackupManager

from src.setup import *
from pathlib import Path

from src.methods.method_selector import select_method
from dataclasses import is_dataclass, fields

from src.utils.iterate_configured_methods import get_configured_method_names


def iterate_structure(obj, prefix=""):
    if is_dataclass(obj):
        for f in fields(obj):
            val = getattr(obj, f.name)
            new_prefix = f"{prefix}.{f.name}" if prefix else f.name
            yield from iterate_structure(val, new_prefix)

    elif isinstance(obj, dict):
        for k, v in obj.items():
            new_prefix = f"{prefix}.{k}" if prefix else str(k)
            yield from iterate_structure(v, new_prefix)

    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            new_prefix = f"{prefix}[{i}]"
            yield from iterate_structure(v, new_prefix)

    else:
        yield prefix, obj


def print_yaml_config(cfg):
    for key, value in iterate_structure(cfg):
        print(f"{key} = {value}")


def print_restraint_setup_groups(cfg) -> None:
    groups = group_restraint_cases_by_class(cfg)
    if len(groups) == 0:
        return

    print("restraint_setup_groups =")
    for group in groups:
        class_system = cfg.get_restraint_system_for_class(group.target_class)
        print(f"  class = {group.target_class}")
        print(f"  pdb = {class_system.pdb}")
        print(f"  receptor_residues = {class_system.receptor_residues}")
        print(f"  ligand_residues = {class_system.ligand_residues}")
        print(f"  n_cases = {len(group.cases)}")
        for case in group.cases:
            print(
                "  case = "
                f"{case.case_name} "
                f"(contribution={case.contribution_name}, index={case.index}, "
                f"kappa={case.kappa}, nstlim={case.nstlim})"
            )


def create_directories(paths: dict) -> None:
    """
    Recursively iterate over all elements in the dictionary and create directories for each path.

    Parameters
    ----------
    paths : dict
        A dictionary containing paths as values or nested dictionaries.
    """
    for key, value in paths.items():
        if isinstance(value, dict):
            # Recursively handle nested dictionaries
            create_directories(value)
        elif isinstance(value, Path):
            # Create the directory if it is a Path object
            value.mkdir(parents=True, exist_ok=True)


def main(cfg_path: str, dry_run: bool = False):

    # 1. load configuration from yaml file and copy yaml input file into setup dir
    cfg = load_config(cfg_path)
    validate_continuation_settings(cfg)
    # cfg = inject_paths(cfg)
    # TODO: change this logic; validate_equilibration_settings(cfg)
    prepare_directories(cfg)
    print_yaml_config(cfg)
    if cfg.restraints is not None:
        print_restraint_setup_groups(cfg)

    if dry_run:
        print("\033[93m[dry-run] Configuration loaded and validated. No setup or submissions were started.\033[0m")
        return

    # 2. perform setup step depending on setup_type and if setup for similar system was already performed
    paths = compute_paths(cfg)
    BackupManager(cfg, paths).backup_run_targets()
    create_directories(paths) # todo:check if this is necessary; probably already in the prepare_directories step, but we can keep it here for safety
    cfg.paths = paths
    ctx = JobContext()
    ctx.paths = paths
    ctx.cfg_path = str(Path(cfg_path).resolve())
    setup_id = setup_simulation(cfg, ctx, Path(cfg_path).resolve())
    # setup_id = None
    print(f"\033[92m[setup] Setup completed with ID {setup_id}\033[0m")
    copy_yaml_input(cfg, cfg_path)

    method_names = get_configured_method_names(cfg)

    for method_name in method_names:
        print(f"running {method_name}")
        method = select_method(method_name, cfg)
        method.launch(ctx)

# 
    # method = select_method(cfg)
    # if method is not None:
    #     method.launch(cfg, ctx)
    # else:
    #     raise ValueError(f"Method {cfg.method.name} not recognized.")
# 
    # # 4. analysis


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load and run a simulation config.")
    parser.add_argument("config", help="Path to the YAML config file.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Load, validate, and print the config without running setup or submitting jobs.",
    )
    args = parser.parse_args()
    main(args.config, dry_run=args.dry_run)
