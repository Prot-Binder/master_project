from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import yaml

from src.utils.paths import *


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


def _as_bool(value: Any, ctx: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "yes", "1", "on"}:
            return True
        if normalized in {"false", "no", "0", "off"}:
            return False
    raise ValueError(f"'{ctx}' must be a boolean.")


@dataclass(frozen=True)
class SystemCfg:
    pdb: Path
    output_prefix: Path
    name: str
    ligand_residues: str
    protein_residues: str
    bond: Optional[str] = None


@dataclass(frozen=True)
class SetupCfg:
    setup: bool
    setup_type: str
    setup_dir: Optional[Path] = None


@dataclass(frozen=True)
class EqCfg:
    execute: bool
    use_cpu: bool
    d: float
    e: float


@dataclass(frozen=True)
class PullIntervalCfg:
    start: float
    end: float
    step: float
    k: float


@dataclass(frozen=True)
class PullCfg:
    d: float
    e: float
    stride: float
    mode: str
    pull_intervals: list[PullIntervalCfg]


@dataclass(frozen=True)
class ClusterCfg:
    exclude_ranks: list[str]


@dataclass(frozen=True)
class USIntervalCfg:
    start: float
    end: float
    step: float
    k: float


@dataclass(frozen=True)
class USCfg:
    d: float
    e: float
    us_intervals: list[USIntervalCfg]


@dataclass(frozen=True)
class RSREMDCfg:
    n_rep: int
    d_scaling: list[float]
    e_scaling: list[float]
    k: float


@dataclass(frozen=True)
class MethodsCfg:
    us: Optional[USCfg]
    rs_remd: Optional[RSREMDCfg]


@dataclass(frozen=False)
class Config:
    tag: str
    test: bool
    cluster: ClusterCfg
    eq: EqCfg
    system: SystemCfg
    setup: SetupCfg
    pull: Optional[PullCfg]
    paths: dict
    methods: MethodsCfg

    def validate(self) -> None:
        if not self.tag or not self.tag.strip():
            raise ValueError("tag must be a non-empty string.")

        if not isinstance(self.test, bool):
            raise ValueError("test must be a boolean.")

        if not self.system.pdb.exists():
            raise ValueError(f"system.pdb does not exist: {self.system.pdb}")

        method_name = self.method.name

        if method_name == "rs_remd":
            if self.methods.rs_remd is None:
                raise ValueError("method.name is 'rs_remd' but no 'methods.rs_remd' section was found.")
            if self.methods.rs_remd.n_rep <= 0:
                raise ValueError("methods.rs_remd.n_rep must be > 0")
            if len(self.methods.rs_remd.d_scaling) != self.methods.rs_remd.n_rep:
                raise ValueError("methods.rs_remd.d_scaling length must equal methods.rs_remd.n_rep")
            if len(self.methods.rs_remd.e_scaling) != self.methods.rs_remd.n_rep:
                raise ValueError("methods.rs_remd.e_scaling length must equal methods.rs_remd.n_rep")
            if self.methods.rs_remd.k <= 0:
                raise ValueError("methods.rs_remd.k must be > 0")
        elif method_name == "us":
            if self.methods.us is None:
                raise ValueError("method.name is 'us' but no 'methods.us' section was found.")
            if len(self.methods.us.us_intervals) == 0:
                raise ValueError("methods.us.us_intervals must be a non-empty list.")
            for idx, interval in enumerate(self.methods.us.us_intervals):
                if interval.k <= 0:
                    raise ValueError(f"methods.us.us_intervals[{idx}].k must be > 0")
                if interval.step <= 0:
                    raise ValueError(f"methods.us.us_intervals[{idx}].step must be > 0")
                if interval.start >= interval.end:
                    raise ValueError(f"methods.us.us_intervals[{idx}].start must be < end")
        elif method_name not in {"eq", "us_remd"}:
            raise ValueError(f"Unknown method name: {method_name}")


def _load_cluster(raw: dict) -> ClusterCfg:
    cluster_raw = raw.get("cluster", {})
    if cluster_raw is None:
        cluster_raw = {}
    cluster_raw = _ensure_mapping(cluster_raw, "cluster")
    exclude_ranks = cluster_raw.get("exclude_ranks", [])
    return ClusterCfg(
        exclude_ranks=[str(x) for x in _ensure_list(exclude_ranks, "cluster.exclude_ranks")]
    )

def _load_setup(raw: dict) -> SetupCfg:
    setup_raw = raw.get("setup", {})
    if setup_raw is None:
        setup_raw = {}
    setup_raw = _ensure_mapping(setup_raw, "setup")
    return SetupCfg(
        setup=_as_bool(setup_raw["setup"], "setup.setup") if "setup" in setup_raw else False,
        setup_type=str(setup_raw["setup_type"]) if "setup_type" in setup_raw else "cluster",
        setup_dir=_as_path(setup_raw["setup_dir"]) if "setup_dir" in setup_raw else None,
    )


def _load_system(raw: dict) -> SystemCfg:
    sys_raw = _ensure_mapping(_require(raw, "system", "top-level"), "system")
    return SystemCfg(
        pdb=_as_path(_require(sys_raw, "pdb", "system")),
        output_prefix=_as_path(sys_raw.get("output_prefix", ".")),
        name=str(_require(sys_raw, "name", "system")),
        ligand_residues=str(_require(sys_raw, "ligand_residues", "system")),
        protein_residues=str(_require(sys_raw, "protein_residues", "system")),
        bond=str(sys_raw["bond"]) if sys_raw.get("bond") is not None else None,
    )


def _load_eq(raw: dict) -> EqCfg:
    eq_raw = raw.get("eq", {})
    if eq_raw is None:
        eq_raw = {}
    eq_raw = _ensure_mapping(eq_raw, "eq")
    return EqCfg(
        execute=_as_bool(eq_raw["execute"], "eq.execute") if "execute" in eq_raw else False,
        use_cpu=_as_bool(eq_raw["use_cpu"], "eq.use_cpu") if "use_cpu" in eq_raw else False,
        d=float(_require(eq_raw, "d", "eq")),
        e=float(_require(eq_raw, "e", "eq")),
    )


def _load_pull(raw: dict) -> Optional[PullCfg]:
    pull_raw = raw.get("pull")
    if pull_raw is None:
        return None

    pull_raw = _ensure_mapping(pull_raw, "pull")
    interval_items = _ensure_list(_require(pull_raw, "pull_intervals", "pull"), "pull.pull_intervals")
    pull_intervals = []
    for index, item in enumerate(interval_items):
        item = _ensure_mapping(item, f"pull.pull_intervals[{index}]")
        pull_intervals.append(
            PullIntervalCfg(
                start=float(_require(item, "start", f"pull.pull_intervals[{index}]")),
                end=float(_require(item, "end", f"pull.pull_intervals[{index}]")),
                step=float(_require(item, "step", f"pull.pull_intervals[{index}]")),
                k=float(_require(item, "k", f"pull.pull_intervals[{index}]")),
            )
        )

    return PullCfg(
        d=float(_require(pull_raw, "d", "pull")),
        e=float(_require(pull_raw, "e", "pull")),
        stride=float(_require(pull_raw, "stride", "pull")),
        mode=str(_require(pull_raw, "mode", "pull")),
        pull_intervals=pull_intervals,
    )


def _load_us(raw: dict, pull: Optional[PullCfg]) -> Optional[USCfg]:
    methods_raw = raw.get("methods", {})
    if methods_raw is None:
        methods_raw = {}
    methods_raw = _ensure_mapping(methods_raw, "methods")

    us_raw = methods_raw.get("us", raw.get("us"))
    if us_raw is None:
        return None

    d_value = None
    e_value = None

    if isinstance(us_raw, dict):
        us_raw = _ensure_mapping(us_raw, "methods.us")
        d_value = us_raw.get("d")
        e_value = us_raw.get("e")
        interval_source = us_raw.get("us_intervals")
        if interval_source is None and {"start", "end", "step", "k"}.issubset(us_raw):
            interval_source = [us_raw]
        if interval_source is None:
            raise ValueError("methods.us must contain 'us_intervals'.")
    else:
        interval_source = _ensure_list(us_raw, "methods.us")

    if d_value is None and pull is not None:
        d_value = pull.d
    if e_value is None and pull is not None:
        e_value = pull.e
    if d_value is None or e_value is None:
        raise ValueError("methods.us requires 'd' and 'e' values, directly or via pull.")

    us_intervals = []
    for index, item in enumerate(_ensure_list(interval_source, "methods.us.us_intervals")):
        item = _ensure_mapping(item, f"methods.us.us_intervals[{index}]")
        us_intervals.append(
            USIntervalCfg(
                start=float(_require(item, "start", f"methods.us.us_intervals[{index}]")),
                end=float(_require(item, "end", f"methods.us.us_intervals[{index}]")),
                step=float(_require(item, "step", f"methods.us.us_intervals[{index}]")),
                k=float(_require(item, "k", f"methods.us.us_intervals[{index}]")),
            )
        )

    return USCfg(
        d=float(d_value),
        e=float(e_value),
        us_intervals=us_intervals,
    )


def _load_rs_remd(raw: dict) -> Optional[RSREMDCfg]:
    methods_raw = raw.get("methods", {})
    if methods_raw is None:
        methods_raw = {}
    methods_raw = _ensure_mapping(methods_raw, "methods")

    rs_raw = methods_raw.get("rs_remd")
    if rs_raw is None:
        return None

    rs_raw = _ensure_mapping(rs_raw, "methods.rs_remd")

    return RSREMDCfg(
        n_rep=int(_require(rs_raw, "n_rep", "methods.rs_remd")),
        d_scaling=[
            float(x)
            for x in _ensure_list(
                _require(rs_raw, "d_scaling", "methods.rs_remd"),
                "methods.rs_remd.d_scaling",
            )
        ],
        e_scaling=[
            float(x)
            for x in _ensure_list(
                _require(rs_raw, "e_scaling", "methods.rs_remd"),
                "methods.rs_remd.e_scaling",
            )
        ],
        k=float(_require(rs_raw, "k", "methods.rs_remd")),
    )


def load_config(path: str | Path) -> Config:
    path = Path(path)
    raw = yaml.safe_load(path.read_text())
    if not isinstance(raw, dict):
        raise ValueError("Top-level YAML must be a mapping (key: value).")

    tag = str(_require(raw, "tag", "top-level"))
    test = _as_bool(raw["test"], "test") if "test" in raw else False

    cluster = _load_cluster(raw)
    system = _load_system(raw)
    eq = _load_eq(raw)
    pull = _load_pull(raw)
    setup = _load_setup(raw)
    methods = MethodsCfg(
        us=_load_us(raw, pull),
        rs_remd=_load_rs_remd(raw),
    )

    cfg = Config(
        tag=tag,
        test=test,
        cluster=cluster,
        eq=eq,
        system=system,
        pull=pull,
        setup=setup,
        paths={},
        methods=methods,
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
    tag must be unique for this (system, method) combination.
    """
    # TODO: iterate over all possible methods
    result_dir = Path(cfg.system.output_prefix) "results" / cfg.system.name / cfg.method.name / cfg.tag
    result_dir.mkdir(parents=True, exist_ok=False)  

    return result_dir


def compute_paths(cfg: Config) -> dict:
    # make a dict out of all paths that are necessary in the future
    result_dir = make_result_dir(cfg)
    method = cfg.method.name
    system_name = cfg.system.name

    paths = {}
    paths["top"] = Path("results") / system_name / "top"
    paths["templates"] = Path("test_templates") if cfg.test else Path("templates")

    # define paths for equilibration
    paths["eq"] = {}
    paths["eq"]["script"] = Path("src") / "methods" / "eq"
    paths["eq"]["root"] = Path("results") / system_name / "eq" / cfg.tag
    paths["eq"]["input"] = paths["eq"]["root"] / "input"
    paths["eq"]["amber"] = paths["eq"]["root"] / "run_output" / "amber"
    paths["eq"]["pmd"] = paths["eq"]["root"] / "run_output" / "pmd"
    paths["eq"]["slurm"] = paths["eq"]["root"] / "run_output" / "slurm"

    # define paths for method
    # TODO: iterate over all the methods specified in the yaml input file
    paths[method] = {}
    paths[method]["script"] = Path("src") / "methods" / method
    paths[method]["setup"] = result_dir / "setup"
    paths[method]["root"] = result_dir
    paths[method]["input"] = result_dir / "input"
    paths[method]["amber"] = paths[method]["root"] / "run_output" / "amber"
    paths[method]["pmd"] = paths[method]["root"] / "run_output" / "pmd"
    paths[method]["slurm"] = paths[method]["root"] / "run_output" / "slurm"

    return paths


def prepare_directores(cfg: Config) -> None:
    for key, path in cfg.paths.items():
        if "dir" in key:
            # TODO: maybe make exist_ok=False later
            path.mkdir(parents=True, exist_ok=True)


def copy_yaml_input(setup_dir: str | Path, cfg_path: str | Path):
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
