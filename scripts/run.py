from src.yaml_config import load_config
# from src.methods import method_factory
from src.utils.paths import make_result_dir, setup_dir, top_dir
from src.setup.system import setup_simulation

from src.setup import *
# delete module later
from dataclasses import is_dataclass, fields

def walk(obj, prefix=""):
    if is_dataclass(obj):
        for f in fields(obj):
            val = getattr(obj, f.name)
            new_prefix = f"{prefix}.{f.name}" if prefix else f.name
            yield from walk(val, new_prefix)

    elif isinstance(obj, dict):
        for k, v in obj.items():
            new_prefix = f"{prefix}.{k}" if prefix else str(k)
            yield from walk(v, new_prefix)

    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            new_prefix = f"{prefix}[{i}]"
            yield from walk(v, new_prefix)

    else:
        yield prefix, obj


def _del_check_yaml_parsing(cfg):
    for key, value in walk(cfg):
        print(f"{key} = {value}")


def main(cfg_path: str):
    # 1. load configuration from yaml file
    cfg = load_config(cfg_path)
    _del_check_yaml_parsing(cfg)
    # get result path
    _result_dir = make_result_dir(cfg.system.name, cfg.method.name, cfg.tag)

    # 2. setup prmtop, restraints, replica topologies and create mdin files
    _setup_dir = setup_dir(_result_dir)
    _setup_dir.mkdir(parents=True, exist_ok=True)
    _top_dir = top_dir(_result_dir)
    _top_dir.mkdir(parents=True, exist_ok=True)
    setup_simulation(cfg, _setup_dir, _top_dir)

    # also copy the .yaml input file somewhere (do not forget)
    # in run.py, after load_config
    # cfg.write(run_dir / "config_used.yaml")

    # result_dir = make_result_dir(cfg)

    # method = method_factory(cfg)
    # method.prepare(run_dir)
    # method.launch(run_dir)
    # method.analyze(run_dir)

    


if __name__ == "__main__":
    import sys
    main(sys.argv[1])
