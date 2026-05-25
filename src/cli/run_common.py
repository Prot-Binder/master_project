from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from pathlib import Path

from src.config import (
    compute_paths,
    load_config,
    validate_continuation_settings,
)
from src.methods.JobContext import JobContext
from src.setup.restraint_cases import group_restraint_cases_by_class
from src.setup.system import setup_simulation
from src.utils.backup_manager import BackupManager
from src.utils.create_directories import create_directories


@dataclass(frozen=True)
class BootstrapResult:
    cfg: object
    ctx: JobContext
    setup_id: str | int


def iterate_structure(obj, prefix=""):
    if is_dataclass(obj):
        for field in fields(obj):
            val = getattr(obj, field.name)
            new_prefix = f"{prefix}.{field.name}" if prefix else field.name
            yield from iterate_structure(val, new_prefix)
    elif isinstance(obj, dict):
        for key, value in obj.items():
            new_prefix = f"{prefix}.{key}" if prefix else str(key)
            yield from iterate_structure(value, new_prefix)
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            new_prefix = f"{prefix}[{idx}]"
            yield from iterate_structure(value, new_prefix)
    else:
        yield prefix, obj


def print_yaml_config(cfg) -> None:
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
                f"(contribution={case.contribution_name}, "
                f"kappa={case.kappa}, nstlim={case.nstlim})"
            )

def bootstrap_run(cfg_path: str, dry_run: bool = False) -> BootstrapResult | None:
    cfg = load_config(cfg_path)
    validate_continuation_settings(cfg)
    print_yaml_config(cfg)
    if cfg.restraints is not None:
        print_restraint_setup_groups(cfg)

    if dry_run:
        print("\033[93m[dry-run] Configuration loaded and validated. No setup or submissions were started.\033[0m")
        return None

    cfg_path_resolved = Path(cfg_path).resolve()
    paths = compute_paths(cfg)
    BackupManager(cfg, paths).backup_run_targets()
    create_directories(paths)
    cfg.paths = paths

    ctx = JobContext()
    ctx.paths = paths
    ctx.cfg_path = str(cfg_path_resolved)

    setup_id = setup_simulation(cfg, ctx, cfg_path_resolved)
    print(f"\033[92m[setup] Setup completed with ID {setup_id}\033[0m")
    return BootstrapResult(cfg=cfg, ctx=ctx, setup_id=setup_id)
