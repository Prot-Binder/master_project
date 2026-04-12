from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, fields
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


def _as_float_list(value: Any, ctx: str) -> list[float]:
    if isinstance(value, list):
        return [float(item) for item in value]
    return [float(value)]


def _as_int(value: Any, ctx: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"'{ctx}' must be an integer.")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"'{ctx}' must be an integer.") from exc


@dataclass(frozen=True)
class SystemCfg:
    pdb: Path
    output_prefix: Path
    name: str
    ligand_residues: str
    protein_residues: str
    bond: Optional[str] = None

@dataclass(frozen=True)
class ClusterCfg:
    exclude_ranks: list[str]

@dataclass(frozen=True)
class SetupCfg:
    setup: bool
    setup_type: str
    setup_dir: Optional[Path] = None

@dataclass(frozen=True)
class MethodCfgBase:
    name: str
    d: list[float]
    e: list[float]
    nstlim: int


@dataclass(frozen=True)
class EqCfg(MethodCfgBase):
    execute: bool
    use_cpu: bool


@dataclass(frozen=True)
class PullIntervalCfg:
    start: float
    end: float
    step: float
    k: float


@dataclass(frozen=True)
class PullCfg(MethodCfgBase):
    stride: float
    mode: str
    pull_intervals: list[PullIntervalCfg]


@dataclass(frozen=True)
class USIntervalCfg:
    start: float
    end: float
    step: float
    k: float


@dataclass(frozen=True)
class USCfg(MethodCfgBase):
    us_intervals: list[USIntervalCfg]


@dataclass(frozen=True)
class RSREMDCfg(MethodCfgBase):
    n_rep: int
    k: float

@dataclass(frozen=True)
class USREMDCfg(MethodCfgBase):
    n_rep: int
    k: float


@dataclass(frozen=True)
class MethodsCfg:
    eq: Optional[EqCfg]
    pull: Optional[PullCfg]
    us: Optional[USCfg]
    us_remd: Optional[USREMDCfg]
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

        if self.eq.execute:
            if len(self.eq.d) == 0 or len(self.eq.e) == 0:
                raise ValueError("eq requires non-empty d and e values.")
            if self.eq.nstlim <= 0:
                raise ValueError("eq.nstlim must be > 0")

        if self.pull is not None:
            if len(self.pull.d) == 0 or len(self.pull.e) == 0:
                raise ValueError("pull requires non-empty d and e values.")
            if self.pull.stride <= 0:
                raise ValueError("pull.stride must be > 0")
            if self.pull.nstlim <= 0:
                raise ValueError("pull.nstlim must be > 0")

        if self.methods.us is not None:
            if len(self.methods.us.d) == 0 or len(self.methods.us.e) == 0:
                raise ValueError("methods.us requires non-empty d and e values.")
            if self.methods.us.nstlim <= 0:
                raise ValueError("methods.us.nstlim must be > 0")
            if len(self.methods.us.us_intervals) == 0:
                raise ValueError("methods.us.us_intervals must be a non-empty list.")
            for idx, interval in enumerate(self.methods.us.us_intervals):
                if interval.k <= 0:
                    raise ValueError(f"methods.us.us_intervals[{idx}].k must be > 0")
                if interval.step <= 0:
                    raise ValueError(f"methods.us.us_intervals[{idx}].step must be > 0")
                if interval.start >= interval.end:
                    raise ValueError(f"methods.us.us_intervals[{idx}].start must be < end")

        for method_name in ("rs_remd", "us_remd"):
            method_cfg = getattr(self.methods, method_name)
            if method_cfg is None:
                continue
            if method_cfg.n_rep <= 0:
                raise ValueError(f"methods.{method_name}.n_rep must be > 0")
            if len(method_cfg.d) != method_cfg.n_rep:
                raise ValueError(f"methods.{method_name}.d must have length as specified in n_rep")
            if len(method_cfg.e) != method_cfg.n_rep:
                raise ValueError(f"methods.{method_name}.e must have length as specified in n_rep")
            if method_cfg.k <= 0:
                raise ValueError(f"methods.{method_name}.k must be > 0")
            if method_cfg.nstlim <= 0:
                raise ValueError(f"methods.{method_name}.nstlim must be > 0")

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
    methods_raw = raw.get("methods", {})
    if methods_raw is None:
        methods_raw = {}
    methods_raw = _ensure_mapping(methods_raw, "methods")

    eq_raw = methods_raw.get("eq", raw.get("eq", {}))
    if eq_raw is None:
        eq_raw = {}
    eq_raw = _ensure_mapping(eq_raw, "eq")
    return EqCfg(
        name=str(eq_raw.get("name", "eq")),
        execute=_as_bool(eq_raw["execute"], "eq.execute") if "execute" in eq_raw else False,
        use_cpu=_as_bool(eq_raw["use_cpu"], "eq.use_cpu") if "use_cpu" in eq_raw else False,
        d=_as_float_list(eq_raw.get("d", []), "eq.d"),
        e=_as_float_list(eq_raw.get("e", []), "eq.e"),
        nstlim=_as_int(eq_raw.get("nstlim", 250000), "eq.nstlim"),
    )


def _load_pull(raw: dict) -> Optional[PullCfg]:
    methods_raw = raw.get("methods", {})
    if methods_raw is None:
        methods_raw = {}
    methods_raw = _ensure_mapping(methods_raw, "methods")

    pull_raw = methods_raw.get("pull", raw.get("pull"))
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
        name=str(pull_raw.get("name", "pull")),
        d=_as_float_list(_require(pull_raw, "d", "pull"), "pull.d"),
        e=_as_float_list(_require(pull_raw, "e", "pull"), "pull.e"),
        nstlim=_as_int(pull_raw.get("nstlim", 2500000), "pull.nstlim"),
        stride=float(_require(pull_raw, "stride", "pull")),
        mode=str(_require(pull_raw, "mode", "pull")),
        pull_intervals=pull_intervals,
    )


def _load_us(raw: dict) -> Optional[USCfg]:
    methods_raw = raw.get("methods", {})
    if methods_raw is None:
        methods_raw = {}
    methods_raw = _ensure_mapping(methods_raw, "methods")

    us_raw = methods_raw.get("us", raw.get("us"))
    if us_raw is None:
        return None

    us_raw = _ensure_mapping(us_raw, "methods.us")
    interval_source = us_raw.get("us_intervals")
    if interval_source is None and {"start", "end", "step", "k"}.issubset(us_raw):
        interval_source = [us_raw]
    if interval_source is None:
        raise ValueError("methods.us must contain 'us_intervals'.")

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
        name=str(us_raw.get("name", "us")),
        d=_as_float_list(_require(us_raw, "d", "methods.us"), "methods.us.d"),
        e=_as_float_list(_require(us_raw, "e", "methods.us"), "methods.us.e"),
        nstlim=_as_int(us_raw.get("nstlim", 25000000), "methods.us.nstlim"),
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
        name=str(rs_raw.get("name", "rs_remd")),
        d=_as_float_list(_require(rs_raw, "d", "methods.rs_remd"),"methods.rs_remd.d"),
        e=_as_float_list(_require(rs_raw, "e", "methods.rs_remd"),"methods.rs_remd.e"),
        nstlim=_as_int(rs_raw.get("nstlim", 2500000), "methods.rs_remd.nstlim"),
        n_rep=int(_require(rs_raw, "n_rep", "methods.rs_remd")),
        k=float(_require(rs_raw, "k", "methods.rs_remd")),
    )

# TODO: maybe adjust it based on if we allow multi k / intervals or not; also a start/stop/end/step would be nice here;
# but more to this later
def _load_us_remd(raw: dict) -> Optional[USREMDCfg]:
    methods_raw = raw.get("methods", {})
    if methods_raw is None:
        methods_raw = {}
    methods_raw = _ensure_mapping(methods_raw, "methods")

    us_remd_raw = methods_raw.get("us_remd")
    if us_remd_raw is None:
        return None

    us_remd_raw = _ensure_mapping(us_remd_raw, "methods.us_remd")

    return USREMDCfg(
        name=str(us_remd_raw.get("name", "us_remd")),
        d=_as_float_list(_require(us_remd_raw, "d", "methods.us_remd"), "methods.us_remd.d"),
        e=_as_float_list(_require(us_remd_raw, "e", "methods.us_remd"), "methods.us_remd.e"),
        nstlim=_as_int(us_remd_raw.get("nstlim", 2500000), "methods.us_remd.nstlim"),
        n_rep=int(_require(us_remd_raw, "n_rep", "methods.us_remd")),
        k=float(_require(us_remd_raw, "k", "methods.us_remd")),
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
    us = _load_us(raw)
    us_remd = _load_us_remd(raw)
    rs_remd = _load_rs_remd(raw)
    methods = MethodsCfg(
        eq=eq,
        pull=pull,
        us=us,
        us_remd=us_remd,
        rs_remd=rs_remd,
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


def make_result_dir(cfg: Config) -> (Path, dict[str, Path]):
    """
    results/<system_name>/<tag>/<method_name>/
    """

    result_dirs: dict[str, Path] = {}

    root_dir = (Path(cfg.system.output_prefix)
                / cfg.system.name
                / cfg.tag)

    for method_field in fields(cfg.methods):
        method_cfg = getattr(cfg.methods, method_field.name)
        if method_cfg is None:
            continue

        method_name = method_field.name
        result_dir = (root_dir / method_name)
        result_dir.mkdir(parents=True, exist_ok=True)
        result_dirs[method_name] = result_dir

    return root_dir, result_dirs

def compute_paths(cfg: Config) -> dict:
    # make a dict out of all paths that are necessary in the future
    root_dir, result_dirs = make_result_dir(cfg)

    paths = {}
    paths["root"] = root_dir
    paths["templates"] = Path("test_templates") if cfg.test else Path("templates")


    # define paths for all specified methods
    for method, result_dir in result_dirs.items():
        paths[method] = {}
        paths[method]["script"] = Path("src") / "methods" / method
        paths[method]["setup"] = result_dir / "setup"
        paths[method]["top"] = result_dir / "top"
        paths[method]["root"] = result_dir
        paths[method]["input"] = result_dir / "input"
        paths[method]["amber"] = paths[method]["root"] / "run_output" / "amber"
        paths[method]["pmd"] = paths[method]["root"] / "run_output" / "pmd"
        paths[method]["slurm"] = paths[method]["root"] / "run_output" / "slurm"

        if method == "rs_remd":
            paths["rs_remd"]["eq"] = paths["rs_remd"]["root"] / "eq"

    return paths


def prepare_directories(cfg: Config) -> None:
    for key, path in cfg.paths.items():
        if "dir" in key:
            # TODO: maybe make exist_ok=False later
            path.mkdir(parents=True, exist_ok=True)


def copy_yaml_input(cfg: Config, cfg_path: str | Path):
    for method_field in fields(cfg.methods):
        method_cfg = getattr(cfg.methods, method_field.name)
        if method_cfg is None:
            continue

        method_name = method_field.name
        setup_dir = cfg.paths[method_name]["setup"]
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
