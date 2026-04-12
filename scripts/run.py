from src.config import load_config, inject_paths, prepare_directories, validate_equilibration_settings, copy_yaml_input, \
    compute_paths
from src.methods.JobContext import JobContext
from src.setup.system import setup_simulation

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


def main(cfg_path: str):

    # 1. load configuration from yaml file and copy yaml input file into setup dir
    cfg = load_config(cfg_path)
    # cfg = inject_paths(cfg)
    # TODO: change this logic; validate_equilibration_settings(cfg)
    prepare_directories(cfg)
    print_yaml_config(cfg)

    # 2. perform setup step depending on setup_type and if setup for similar system was already performed
    paths = compute_paths(cfg)
    create_directories(paths) # todo:check if this is necessary; probably already in the prepare_directories step, but we can keep it here for safety
    cfg.paths = paths
    ctx = JobContext()
    ctx.paths = paths
    setup_id = setup_simulation(cfg, ctx, Path(cfg_path).resolve())
    # setup_id = None
    print(f"\033[92m[setup] Setup completed with ID {setup_id}\033[0m")
    copy_yaml_input(cfg, cfg_path)

    # # 3. select and execute the desired method
    # # if equilibration is requested, perform equilibration first
    # if cfg.method.eq:
    #    print("running equilibration")

    # method_names = get_configured_method_names(cfg)
    method_names = []
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
    import sys
    main(sys.argv[1])
