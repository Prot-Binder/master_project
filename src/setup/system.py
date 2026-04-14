import shutil
import shlex
import subprocess
import sys
from dataclasses import fields
from pathlib import Path
from src.setup.tleap import TLeapPaths, run_tleap
from src.setup.hmr import ParmEdPaths, run_hmr
from src.setup.restraints import create_restraints
from src.setup.generate_topology import generate_scaled_top_files
from src.setup.generate_input_files import generate_inputs
from src.utils.iterate_configured_methods import get_configured_method_names

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


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]

def create_box_and_prmtop(cfg, ctx, method_name: str) -> tuple[Path, Path, int]:
    setup_dir = ctx.paths[method_name]["setup"]

    tleap_paths = TLeapPaths(
        template_tleap=Path("templates/tleap.in.tpl"),
        ff_leaprc_cyclic=Path("forcefield/leaprc.cyclic.ff14SB"),
    )

    if cfg.setup.setup_type == "cluster":
        cluster=""
    else:
        cluster="cluster/"
    prmtop, rst, n_ions_each = run_tleap(
        cluster=cluster,
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

    return prmtop, rst, n_ions_each

def _run_setup_pipeline(cfg, ctx) -> None:
    method_names = get_configured_method_names(cfg)
    if len(method_names) == 0:
        raise ValueError("No methods configured in cfg.methods.")
    
    first_method = method_names[0]
    first_setup_dir = ctx.paths[first_method]["setup"].resolve()
    """
    # run tleap and HMR
    create_box_and_prmtop(cfg, ctx, first_method)
    
    # create restraint template files
    system_pdb = first_setup_dir / "system.pdb"
    create_restraints(first_setup_dir, system_pdb, cfg.system.protein_residues, cfg.system.ligand_residues)
    print(f"\033[92m[setup] Shared setup prepared in {first_method}\033[0m")
    
    #copy shared setup files from first method to all other methods;
    for method_name in method_names[1:]:
        dest_setup_dir = ctx.paths[method_name]["setup"].resolve()
        _replace_directory(first_setup_dir, dest_setup_dir)
        print(f"\033[92m[setup] Copied setup files from {first_method} to {method_name}\033[0m")

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
            ":" + cfg.system.protein_residues,
            ":" + cfg.system.ligand_residues,
        )
        print(f"\033[92m[setup] Generated scaled prmotp file(s) for {method_name}\033[0m")
    """
    for method_name in method_names:
       generate_inputs(str(method_name), cfg, ctx)
       print(f"\033[92m[setup] Input files copied and adjusted for {method_name}\033[0m")


def _submit_setup_job_and_wait(cfg, ctx, cfg_path: Path) -> str:
    method_names = get_configured_method_names(cfg)
    if len(method_names) == 0:
        raise ValueError("No methods configured in cfg.methods.")

    slurm_dir = ctx.paths["root"]

    project_root = _project_root().resolve()
    python_exe = Path(sys.executable).resolve()

    wrap_cmd = (
        "bash -lc 'cd {root} && "
        "{python} -m src.setup.run_setup_job {cfg_path}'"
    ).format(
        root=shlex.quote(str(project_root)),
        python=shlex.quote(str(python_exe)),
        cfg_path=shlex.quote(str(cfg_path.resolve())),
    )

    sbatch_cmd = [
        "sbatch",
        "--parsable",
        f"--job-name=setup_{cfg.system.name}_{cfg.tag}",
        "--nodes=1",
        "--ntasks=1",
        "--cpus-per-task=1",
        "--time=00:30:00",
        f"--output={slurm_dir / 'slurm-%j_setup.out'}",
        "--wrap",
        wrap_cmd,
    ]

    result = subprocess.run(
        sbatch_cmd,
        check=True,
        capture_output=True,
        text=True,
        cwd=project_root,
    )
    job_id = result.stdout.strip()
    ctx.setup_job_id = job_id
    print(f"\033[92m[setup] Cluster setup finished via Slurm job {job_id}\033[0m")
    return job_id


def setup_simulation(cfg, ctx, cfg_path: Path):
    setup_type = cfg.setup.setup_type.lower()
    if setup_type == "local":
        _run_setup_pipeline(cfg, ctx)
        return 0
    elif setup_type == "cluster":
        return _submit_setup_job_and_wait(cfg, ctx, cfg_path)
    else:
        raise ValueError(f"Unknown setup.setup_type: {cfg.setup.setup_type}")
