from __future__ import annotations

from re import template

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
class RestraintsCfg:
    k: float
    step_size: float
    min: float
    max: float


@dataclass(frozen=True)
class MethodCfg:
    name: str  # "rs_remd" | "us" | ...

@dataclass(frozen=True)
class ReplicaScaling:
    n_rep: int
    d_scaling: list[float]
    e_scaling: list[float]

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
    use_restraints_range: bool


@dataclass(frozen=False)
class Config:
    tag: str
    system: SystemCfg
    restraints: RestraintsCfg
    method: MethodCfg
    replica_scaling: ReplicaScaling
    paths: dict
    rs_remd: Optional[RSREMDCfg] = None
    us: Optional[USCfg] = None

    def validate(self) -> None:
        if not self.tag or not self.tag.strip():
            raise ValueError("tag must be a non-empty string.")

        if not self.system.pdb.exists():
            raise ValueError(f"system.pdb does not exist: {self.system.pdb}")

        if self.restraints.k <= 0:
            raise ValueError("restraints.k must be > 0")
        if self.restraints.step_size <= 0:
            raise ValueError("restraints.step_size must be > 0")
        if self.restraints.min >= self.restraints.max:
            raise ValueError("restraints.min must be < restraints.max")

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
            if self.us.start >= self.us.end:
                raise ValueError("us.start must be < us.end")

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

    # system
    sys_raw = _ensure_mapping(_require(raw, "system", "top-level"), "system")
    system = SystemCfg(
        pdb=_as_path(_require(sys_raw, "pdb", "system")),
        name=str(_require(sys_raw, "name", "system")),
        ligand_residues=str(_require(sys_raw, "ligand_residues", "system")),
        protein_residues=str(_require(sys_raw, "protein_residues", "system")),
        bond=sys_raw.get("bond"),
    )

    # restraints (NO typo support; step_size is required)
    r_raw = _ensure_mapping(_require(raw, "restraints", "top-level"), "restraints")
    restraints = RestraintsCfg(
        k=float(_require(r_raw, "k", "restraints")),
        step_size=float(_require(r_raw, "step_size", "restraints")),
        min=float(_require(r_raw, "min", "restraints")),
        max=float(_require(r_raw, "max", "restraints")),
    )

    # method
    m_raw = _ensure_mapping(_require(raw, "method", "top-level"), "method")
    method = MethodCfg(name=str(_require(m_raw, "name", "method")))

    # replica scaling
    rs_raw = _ensure_mapping(_require(raw, "replica_scaling", "top-level"), "replica_scaling")
    replica_scaling = ReplicaScaling(
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
        us_raw = _ensure_mapping(raw["us"], "us")
        us = USCfg(
            start=float(_require(us_raw, "start", "us")),
            end=float(_require(us_raw, "end", "us")),
            # TODO: use this somewhere in the setup
            use_restraints_range=bool(_require(us_raw, "use_restraints_range", "us")),
        )

    cfg = Config(
        tag=tag,
        system=system,
        restraints=restraints,
        method=method,
        replica_scaling=replica_scaling,
        paths={},
        rs_remd=rs_remd,
        us=us,
    )
    cfg.validate()
    return cfg

def inject_paths(cfg: Config) -> Config:
    #if "paths" in cfg:
    #    raise RuntimeError("Paths already added to config")

    result_root = make_result_dir(cfg.system.name, cfg.method.name, cfg.tag)
    cfg.paths = {
        # roots
        "project_root": Path.cwd(), #TODO: change this maybe, not sure about it
        "results_root": result_root,
        "templates_root": template_dir(),
        # method-level
        "eq_dir": eq_dir(result_root, cfg.tag),
        "top_dir": top_dir(result_root),
        "setup_dir": setup_dir(result_root),
    }
    return cfg

def prepare_directores(cfg: Config) -> None:
    # create necessary directories
    for key, path in cfg.paths.items():
        if "dir" in key:
            # TODO: maybe make exist_ok=False later
            path.mkdir(parents=True, exist_ok=True)
