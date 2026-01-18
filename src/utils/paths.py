# src/paths.py
from pathlib import Path

def make_result_dir(system_name: str, method_name: str, tag: str) -> Path:
    """
    results/<system_name>/<method_name>/<tag>/
    Tag must be unique for this (system, method) combination.
    """
    result_dir = Path("results") / system_name / method_name / tag
    result_dir.mkdir(parents=True, exist_ok=True)  # fail if already exists
    return result_dir

def setup_dir(result_dir: Path) -> Path:
    return result_dir / "setup"

def eq_dir(result_dir: Path, tag: str) -> Path:
    # return result_dir / "eq"
    return result_dir.parent.parent / "eq" / tag

def prod_dir(result_dir: Path) -> Path:
    return result_dir / "prod"

def analysis_dir(result_dir: Path) -> Path:
    return result_dir / "analysis"

def replicas_dir(result_dir: Path) -> Path:
    return result_dir / "replicas"

def replica_dir(result_dir: Path, i: int) -> Path:
    return result_dir / f"rep{i:02d}"

def top_dir(result_dir: Path) -> Path:
    # get method name from result_dir
    system_name = str(result_dir).split("/")[1]
    return Path(result_dir.parts[0]) / system_name / "top"

def template_dir() -> Path:
    return Path("templates")

def output_dir(result_dir: Path) -> Path:
    return result_dir / "run_output"

def script_dir(method_name: str):
    return Path("src") / "methods" / method_name

def eq_script_dir():
    return Path("src") / "methods" / "eq"