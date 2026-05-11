#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEST_SUITE_DIR = PROJECT_ROOT / "input" / "yaml_input" / "test_suite"


@dataclass(frozen=True)
class SuiteCase:
    label: str
    entrypoint: Path
    config: Path


def build_cases(only: str) -> list[SuiteCase]:
    run_py = PROJECT_ROOT / "scripts" / "run.py"
    run_restraints_py = PROJECT_ROOT / "scripts" / "run_restraints.py"

    method_cases = [
        SuiteCase("methods_eq", run_py, TEST_SUITE_DIR / "methods_eq.yaml"),
        SuiteCase("methods_pull", run_py, TEST_SUITE_DIR / "methods_pull.yaml"),
        SuiteCase("methods_us", run_py, TEST_SUITE_DIR / "methods_us.yaml"),
        SuiteCase("methods_us_remd", run_py, TEST_SUITE_DIR / "methods_us_remd.yaml"),
        SuiteCase("methods_rs_remd", run_py, TEST_SUITE_DIR / "methods_rs_remd.yaml"),
        SuiteCase("methods_all", run_py, TEST_SUITE_DIR / "methods_all.yaml"),
    ]

    restraint_cases = [
        SuiteCase("restraints_receptor", run_restraints_py, TEST_SUITE_DIR / "restraints_receptor.yaml"),
        SuiteCase("restraints_ligand", run_restraints_py, TEST_SUITE_DIR / "restraints_ligand.yaml"),
        SuiteCase("restraints_complex", run_restraints_py, TEST_SUITE_DIR / "restraints_complex.yaml"),
        SuiteCase("restraints_all_classes", run_restraints_py, TEST_SUITE_DIR / "restraints_all_classes.yaml"),
    ]

    if only == "methods":
        return method_cases
    if only == "restraints":
        return restraint_cases
    return method_cases + restraint_cases


def build_env() -> dict[str, str]:
    env = os.environ.copy()
    existing = env.get("PYTHONPATH")
    root_str = str(PROJECT_ROOT)
    env["PYTHONPATH"] = root_str if not existing else f"{root_str}:{existing}"
    return env


def run_case(case: SuiteCase, *, dry_run: bool, env: dict[str, str]) -> int:
    cmd = [sys.executable, str(case.entrypoint), str(case.config)]
    if dry_run:
        cmd.append("--dry-run")

    mode = "dry-run" if dry_run else "submit"
    print(f"[test-suite] {mode} {case.label}: {case.config.name}")
    result = subprocess.run(
        cmd,
        cwd=PROJECT_ROOT,
        env=env,
    )
    return result.returncode


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run all YAML configs in input/yaml_input/test_suite one after another."
    )
    parser.add_argument(
        "--submit",
        action="store_true",
        help="Run the suite normally. By default, the suite runs in --dry-run mode.",
    )
    parser.add_argument(
        "--only",
        choices=("all", "methods", "restraints"),
        default="all",
        help="Limit the suite to method configs or restraint configs.",
    )
    parser.add_argument(
        "--keep-going",
        action="store_true",
        help="Continue after a failure and report all failing configs at the end.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Print the configs that would be executed and exit.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cases = build_cases(args.only)

    missing = [case.config for case in cases if not case.config.is_file()]
    if missing:
        for path in missing:
            print(f"[test-suite] missing config: {path}")
        return 1

    if args.list:
        for case in cases:
            print(f"{case.label}: {case.config}")
        return 0

    env = build_env()
    dry_run = not args.submit
    failures: list[SuiteCase] = []

    for case in cases:
        returncode = run_case(case, dry_run=dry_run, env=env)
        if returncode == 0:
            continue
        failures.append(case)
        if not args.keep_going:
            print(f"[test-suite] failed: {case.label}")
            return returncode

    if failures:
        print("[test-suite] failures:")
        for case in failures:
            print(f"  - {case.label}: {case.config}")
        return 1

    print(f"[test-suite] completed {len(cases)} config(s) successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
