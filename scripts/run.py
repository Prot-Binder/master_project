from src.config import load_config, inject_paths, prepare_directores, validate_equilibration_settings
# from src.methods import method_factory
from src.utils.paths import make_result_dir, setup_dir, top_dir
from src.setup.system import setup_simulation

from src.setup import *

# from src.methods.us import USMethod
from src.methods.method_selector import select_method, create_eq
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
    cfg = inject_paths(cfg)
    # validate_equilibration_settings(cfg)
    prepare_directores(cfg)
  
    # TODO: delete this later
    _del_check_yaml_parsing(cfg)

    # get result path
    # _result_dir = make_result_dir(cfg.system.name, cfg.method.name, cfg.tag)
    # print(str(_result_dir))

    # TODO: change exist_ok to False
    # 2. setup prmtop, restraints, replica topologies and create mdin files
    if cfg.method.setup:
        # _setup_dir = setup_dir(_result_dir)
        # _setup_dir.mkdir(parents=True, exist_ok=True)
        # _top_dir = top_dir(_result_dir)
        # _top_dir.mkdir(parents=True, exist_ok=True)
        setup_simulation(cfg)
# 
    # # 3. select and execute the desired method
    if cfg.method.eq:
        print("running equilibration")
        # execute eq methodology pass job id for future simulations
        eq_method = create_eq(cfg)
        cfg.method.eq_id = int(eq_method.launch(cfg))
        
    method = select_method(cfg)
    if method is None:
        print("selected equilibration only. Program terminating as expected")
        # method.launch(cfg)
    else:
        print(f"method is {cfg.method.name}")
        method.launch(cfg)

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
