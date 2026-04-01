import shutil
from dataclasses import fields

from src.setup.tleap import TLeapPaths, run_tleap
from src.setup.hmr import ParmEdPaths, run_hmr
from src.setup.restraints import create_restraints
from src.setup.generate_topology import generate_scaled_top_files
from src.setup.generate_input_files import generate_inputs
from pathlib import Path


def _configured_method_names(cfg) -> list[str]:
    method_names = []
    for method_field in fields(cfg.methods):
        method_cfg = getattr(cfg.methods, method_field.name)
        if method_cfg is not None:
            method_names.append(method_field.name)
    return method_names


def _replace_directory(src_dir: Path, dest_dir: Path) -> None:
    if src_dir.resolve() == dest_dir.resolve():
        return

    if dest_dir.exists():
        shutil.rmtree(dest_dir)

    shutil.copytree(src_dir, dest_dir)


def _get_method_cfg(cfg, method_name: str):
    method_cfg = getattr(cfg.methods, method_name, None)
    if method_cfg is None:
        raise ValueError(f"Method '{method_name}' is not configured.")
    return method_cfg


def _get_num_replicas(method_cfg) -> int:
    if hasattr(method_cfg, "n_rep"):
        return int(method_cfg.n_rep)

    d_len = len(method_cfg.d)
    e_len = len(method_cfg.e)
    if d_len != e_len and d_len != 1 and e_len != 1:
        raise ValueError("Method d/e lengths are incompatible for topology generation.")
    return max(d_len, e_len)

def create_box_and_prmtop(cfg, ctx, method_name: str) -> tuple[Path, Path, int]:
    setup_dir = ctx.paths[method_name]["setup"]

    tleap_paths = TLeapPaths(
        template_tleap=Path("templates/tleap.in.tpl"),
        ff_leaprc_cyclic=Path("forcefield/leaprc.cyclic.ff14SB"),
    )

    prmtop, rst, n_ions_each = run_tleap(
        setup_dir=setup_dir,
        pdb_path=cfg.system.pdb,
        bond=cfg.system.bond,
        paths=tleap_paths,
    )

    parmed_paths = ParmEdPaths(template=Path("templates/HMR.parmed.tpl"))
    run_hmr(
        setup_dir=setup_dir,
        in_prmtop=prmtop,
        out_prmtop=setup_dir / "prmtop",
        paths=parmed_paths,
    )

def run_setup_steps(cfg, ctx, method_name: str) -> None:
    setup_dir = ctx.paths[method_name]["setup"]
    method_cfg = _get_method_cfg(cfg, method_name)

    tleap_paths = TLeapPaths(
        template_tleap=Path("templates/tleap.in.tpl"),
        ff_leaprc_cyclic=Path("forcefield/leaprc.cyclic.ff14SB"),
    )

    prmtop, rst, n_ions_each = run_tleap(
        setup_dir=setup_dir,
        pdb_path=cfg.system.pdb,
        bond=cfg.system.bond,
        paths=tleap_paths,
    )

    parmed_paths = ParmEdPaths(template=Path("templates/HMR.parmed.tpl"))
    run_hmr(
        setup_dir=setup_dir,
        in_prmtop=prmtop,
        out_prmtop=setup_dir / "prmtop",
        paths=parmed_paths,
    )

    system_pdb = setup_dir / "system.pdb"
    create_restraints(setup_dir, system_pdb, cfg.system.protein_residues, cfg.system.ligand_residues)

    # TODO: adjust topology file generation soon, i.e. make it for every method available (also eq and pull)
    generate_scaled_top_files(
        setup_dir / "prmtop",
        _get_num_replicas(method_cfg),
        method_cfg.d,
        method_cfg.e,
        setup_dir / "system.rst",
        ctx.paths["top"] / "prmtop",
        ":" + cfg.system.protein_residues,
        ":" + cfg.system.ligand_residues,
    )

def setup_simulation(cfg, ctx):
    # TODO maybe change so that we maybe only use eq and maybe pull stuff?
    method_names = _configured_method_names(cfg)
    if len(method_names) == 0:
        raise ValueError("No methods configured in cfg.methods.")

    first_method = method_names[0]
    first_setup_dir = ctx.paths[first_method]["setup"].resolve()

    create_box_and_prmtop(cfg, ctx, first_method)
    print(f"\033[92m[setup] Shared setup prepared in {first_method}\033[0m")

    for method_name in method_names[1:]:
        dest_setup_dir = ctx.paths[method_name]["setup"].resolve()
        _replace_directory(first_setup_dir, dest_setup_dir)
        print(f"\033[92m[setup] Copied prmotp files from {first_method} to {method_name}\033[0m")

    # TODO: change it so that restraints are generated

    # TODO: change it so that top files are generated for all methods, not only rs_remd (but also eq and pull, us etc.)
    for method_name in method_names:
        setup_dir = cfg.paths[method_name]["setup"]
        method_cfg = _get_method_cfg(cfg, method_name)
        generate_scaled_top_files(
            setup_dir / "prmtop",
            len(method_cfg.d),
            method_cfg.d,
            method_cfg.e,
            setup_dir / "system.rst",
            cfg.paths[method_name]["top"] / "prmtop",
            ctx.paths["top"] / "prmtop",
            ":" + cfg.system.protein_residues,
            ":" + cfg.system.ligand_residues,
        )
        print(f"\033[92m[setup] Generated scaled prmotp file(s) for {method_name}\033[0m")
    # TODO: change this
    #for method_name in method_names:
    #    generate_inputs(method_name, cfg, ctx)
    #    print(f"\033[92m[setup] Input files copied and adjusted for {method_name}\033[0m")

    # TODO: change it so that also pull is considered
    #if cfg.eq.execute:
    #    generate_inputs("eq", cfg, ctx)
    #    print(f"\033[92m[setup] Input files copied and adjusted for eq\033[0m")
