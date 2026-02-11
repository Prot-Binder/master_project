from __future__ import annotations

import shutil

# from re import template

# from src.utils.paths import make_result_dir, setup_dir, top_dir
from src.utils.paths import *
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional
import os
import yaml


# -------------------------
# Helpers
# -------------------------

def _require(d: dict, key: str, ctx: str) -> Any:
    if key not in d:
        raise ValueError(f"Missing required key '{key}' in {ctx}")
    return d[key]


def _as_path(p: Any) -> Path:
    if p is None:
        raise ValueError("Expected a path-like value, got None")
    s = os.path.expandvars(str(p))
    s = os.path.expanduser(s)
    return Path(s)


def _ensure_mapping(x: Any, ctx: str) -> dict:
    if not isinstance(x, dict):
        raise ValueError(f"'{ctx}' must be a mapping (YAML dict).")
    return x


def _ensure_list(x: Any, ctx: str) -> list:
    if not isinstance(x, list):
        raise ValueError(f"'{ctx}' must be a list.")
    return x


# -------------------------
# Global config sections
# -------------------------

@dataclass(frozen=True)
class SystemCfg:
    pdb: Path
    name: str
    ligand_residues: str
    protein_residues: str
    bond: Optional[str] = None

@dataclass(frozen=True)
class MethodCfg:
    name: str  # "rs_remd" | "us" | ...
    setup: bool
    setup_type: str # cluster or local
    eq: bool
    setup_dir: Optional[Path] = None

@dataclass(frozen=True)
class ReplicaScalingCfg:
    n_rep: int
    d_scaling: list[float]
    e_scaling: list[float]

@dataclass(frozen=True)
class ClusterCfg:
    exclude_ranks: list[str]

# -------------------------
# Method-specific configs
# -------------------------

@dataclass(frozen=True)
class RSREMDCfg:
    n_rep: int
    replicas: list[int]


@dataclass(frozen=True)
class USCfg:
    start: float
    end: float
    step: float
    replica_scaling: int
    k: float


@dataclass(frozen=False)
class Config:
    tag: str
    cluster: ClusterCfg
    system: SystemCfg
    method: MethodCfg
    replica_scaling: ReplicaScalingCfg
    paths: dict
    rs_remd: Optional[RSREMDCfg] = None
    us: list[Optional[USCfg]] = None

    def validate(self) -> None:
        if not self.tag or not self.tag.strip():
            raise ValueError("tag must be a non-empty string.")

        if not self.system.pdb.exists():
            raise ValueError(f"system.pdb does not exist: {self.system.pdb}")

        m = self.method.name

        if m == "rs_remd":
            if self.rs_remd is None:
                raise ValueError("method.name is 'rs_remd' but no 'rs_remd:' section was found.")
            if self.rs_remd.n_rep <= 0:
                raise ValueError("rs_remd.n_rep must be > 0")
            if len(self.rs_remd.replicas) != self.rs_remd.n_rep:
                raise ValueError(
                    f"rs_remd.replicas length ({len(self.rs_remd.replicas)}) "
                    f"must equal rs_remd.n_rep ({self.rs_remd.n_rep})."
                )
            if len(set(self.rs_remd.replicas)) != len(self.rs_remd.replicas):
                raise ValueError("rs_remd.replicas contains duplicates (should be unique).")
            if any(x < 0 for x in self.rs_remd.replicas):
                raise ValueError("rs_remd.replicas must be non-negative integers.")

        elif m == "us":
            if self.us is None:
                raise ValueError("method.name is 'us' but no 'us:' section was found.")
            if not isinstance(self.us, list) or len(self.us) == 0:
                raise ValueError("us must be a non-empty list.")
            for idx, r in enumerate(self.us):
                if r.k <= 0:
                    raise ValueError(f"us[{idx}].k must be > 0")
                if r.step_size <= 0:
                    raise ValueError(f"us[{idx}].step_size must be > 0")
                if r.start >= r.end:
                    raise ValueError(f"us[{idx}].start must be < us[{idx}].end")
                if r.replica_scaling <= 0:
                    raise ValueError(f"us[{idx}].replica_scaling must be > 0")
        else:
            raise ValueError(f"Unknown method name: {m}")


# -------------------------
# Parsing
# -------------------------

def load_config(path: str | Path) -> Config:
    path = Path(path)
    raw = yaml.safe_load(path.read_text())
    if not isinstance(raw, dict):
        raise ValueError("Top-level YAML must be a mapping (key: value).")

    tag = str(_require(raw, "tag", "top-level"))

    # cluster
    cluster_raw = _ensure_mapping(_require(raw, "cluster", "top-level"), "cluster")
    cluster = ClusterCfg(
        exclude_ranks=[str(x) for x in _ensure_list(_require(cluster_raw, "exclude_ranks", "cluster"), "cluster.exclude_ranks")],

    )

    # system
    sys_raw = _ensure_mapping(_require(raw, "system", "top-level"), "system")
    system = SystemCfg(
        pdb=_as_path(_require(sys_raw, "pdb", "system")),
        name=str(_require(sys_raw, "name", "system")),
        ligand_residues=str(_require(sys_raw, "ligand_residues", "system")),
        protein_residues=str(_require(sys_raw, "protein_residues", "system")),
        bond=sys_raw.get("bond"),
    )

    # method
    m_raw = _ensure_mapping(_require(raw, "method", "top-level"), "method")
    method = MethodCfg(
        name=str(_require(m_raw, "name", "method")),
        eq=bool(_require(m_raw, "eq", "method")),
        setup=bool(_require(m_raw, "setup", "method")), # TODO: think of deleting this filed, may be redundant
        setup_dir=Path(m_raw["setup_dir"]) if "setup_dir" in m_raw and m_raw["setup_dir"] is not None else None,
        setup_type=str(_require(m_raw, "setup_type", "method")),
    )

    # replica scaling
    rs_raw = _ensure_mapping(_require(raw, "replica_scaling", "top-level"), "replica_scaling")
    replica_scaling = ReplicaScalingCfg(
        n_rep=int(_require(rs_raw, "n_rep", "replica_scaling")),
        d_scaling=[float(x) for x in _ensure_list(_require(rs_raw, "d_scaling", "replica_scaling"), "replica_scaling.d_scaling")],
        e_scaling=[float(x) for x in _ensure_list(_require(rs_raw, "e_scaling", "replica_scaling"), "replica_scaling.e_scaling")],
    )

    # method-specific sections
    rs_remd = None
    if "rs_remd" in raw and raw["rs_remd"] is not None:
        rs_raw = _ensure_mapping(raw["rs_remd"], "rs_remd")
        replicas = _ensure_list(_require(rs_raw, "replicas", "rs_remd"), "rs_remd.replicas")
        rs_remd = RSREMDCfg(
            n_rep=int(_require(rs_raw, "n_rep", "rs_remd")),
            replicas=[int(x) for x in replicas],
        )

    us = None
    if "us" in raw and raw["us"] is not None:
        us_list_raw = _ensure_list(raw["us"], "us")
        us = []
        for i, item in enumerate(us_list_raw):
            item_map = _ensure_mapping(item, f"us[{i}]")
            us.append(USCfg(
                start=float(_require(item_map, "start", f"us[{i}]")),
                end=float(_require(item_map, "end", f"us[{i}]")),
                step=float(_require(item_map, "step", f"us[{i}]")),
                replica_scaling=int(_require(item_map, "replica_scaling", f"us[{i}]")),
                k=float(_require(item_map, "k", f"us[{i}]")),
            ))

    cfg = Config(
        tag=tag,
        cluster=cluster,
        system=system,
        method=method,
        replica_scaling=replica_scaling,
        paths={},
        rs_remd=rs_remd,
        us=us,
    )
    cfg.validate()
    return cfg

# TODO: possibly delete thsi
def inject_paths(cfg: Config) -> Config:
    #if "paths" in cfg:
    #    raise RuntimeError("Paths already added to config")

    result_root = make_result_dir(cfg.system.name, cfg.method.name, cfg.tag)
    cfg.paths = {
        # roots
        "project_root": Path.cwd(), #TODO: change this maybe, not sure about it
        "results_root": result_root,
        "templates_root": template_dir(),
        "script_root": script_dir(cfg.method.name),
        "eq_script_root": eq_script_dir(),

        # method-level
        "eq_dir": eq_dir(result_root, cfg.tag),
        "top_dir": top_dir(result_root),
        "setup_dir": setup_dir(result_root),
        "output_dir": output_dir(result_root),
    }
    return cfg

def make_result_dir(cfg: Config) -> Path:
    """
    results/<system_name>/<method_name>/<tag>/
    Tag must be unique for this (system, method) combination.
    """
    result_dir = Path("results") / cfg.system.name / cfg.method.name / cfg.tag
    result_dir.mkdir(parents=True, exist_ok=True)  # fail if already exists
    return result_dir

def compute_paths(cfg: Config) -> dict:
    # make a dict out of all paths that are necessary in the future
    result_dir = make_result_dir(cfg)
    method = cfg.method.name
    system_name : str = cfg.system.name

    paths = {}
    paths["top"] = Path("results") / system_name / "top"
    paths["templates"] = Path("templates")

    # define paths for equilibration
    paths["eq"] = {}
    paths["eq"]["script"] = Path("src") / "methods" / "eq"
    paths["eq"]["root"] = Path("results") / system_name / "eq" / cfg.tag
    paths["eq"]["input"] = paths["eq"]["root"] / "input"
    paths["eq"]["amber"] = paths["eq"]["root"] / "run_output" / "amber"
    paths["eq"]["pmd"] = paths["eq"]["root"] / "run_output" / "pmd"
    paths["eq"]["slurm"] = paths["eq"]["root"] / "run_output" / "slurm"

    # define paths for method
    paths[method] = {}
    paths[method]["script"] = Path("src") / "methods" / method
    paths[method]["setup"] = result_dir / "setup"
    paths[method]["root"] = result_dir
    paths[method]["input"] = result_dir/ "input"

    paths[method]["amber"] = paths[method]["root"] / "run_output" / "amber"
    paths[method]["pmd"] = paths[method]["root"] / "run_output" / "pmd"
    paths[method]["slurm"] = paths[method]["root"] / "run_output" / "slurm"

    return paths

def prepare_directores(cfg: Config) -> None:
    # create necessary directories
    for key, path in cfg.paths.items():
        if "dir" in key:
            # TODO: maybe make exist_ok=False later
            path.mkdir(parents=True, exist_ok=True)

def copy_yaml_input(setup_dir: str | Path, cfg_path: str | Path):
    # copy the .yaml input file to results directory
    shutil.copy2(cfg_path, setup_dir)

def validate_equilibration_settings(cfg: Config):
    """
    this method checks if an equilibration already occured or not. The results of this method are shared among multiple methods, hence
    results may exist from a previous run that can be reused.
    This method needs to be invoked before creating all the directories and the setup step.
    """
    eq_dir: Path = cfg.paths["eq_dir"]

    # TODO: Think more of this logic, as files are problably already copied due to setup, without anything else being run

    if cfg.method.eq:
        # Equilibration IS specified in the .yaml file → directory must not exist or must be empty
        if eq_dir.is_dir() and any(eq_dir.iterdir()):
            raise FileExistsError(
                f"Equilibration directory already exists and is not empty: {eq_dir}"
            )

    else:
        # Equilibration NOT specified → directory must exist and files like inpcrd0-4 and refc must be present
        if not eq_dir.is_dir():
            raise FileNotFoundError(
                f"Equilibration directory does not exist: {eq_dir}"
            )

        required_files = ["inpcrd0", "inpcrd1", "inpcrd2", "inpcrd3", "inpcrd4", "refc"]
        missing_files = [f for f in required_files if not (eq_dir / f).is_file()]
        if len(missing_files) > 0:
            raise FileNotFoundError(
                f"Equilibration directory is missing required files: {missing_files}"
            )
