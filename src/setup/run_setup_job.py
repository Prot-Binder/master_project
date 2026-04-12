from __future__ import annotations

import sys
from pathlib import Path

from scripts.run import create_directories
from src.config import compute_paths, load_config
from src.methods.JobContext import JobContext
from src.setup.system import _run_setup_pipeline


def main(cfg_path: str) -> None:
    cfg = load_config(cfg_path)
    cfg.paths = compute_paths(cfg)
    create_directories(cfg.paths)

    ctx = JobContext()
    ctx.paths = cfg.paths

    _run_setup_pipeline(cfg, ctx)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python src/setup/run_setup_job.py <config.yaml>")
    main(sys.argv[1])
