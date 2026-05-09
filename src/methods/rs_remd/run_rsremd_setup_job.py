from __future__ import annotations

import sys
from pathlib import Path

from src.config import compute_paths, load_config
from src.methods.JobContext import JobContext
from src.methods.rs_remd.rs_remd_setup import setup_rs_remd
from src.utils.create_directories import create_directories


def main(cfg_path: str) -> None:
    cfg = load_config(cfg_path)
    cfg.paths = compute_paths(cfg)
    create_directories(cfg.paths)

    ctx = JobContext()
    ctx.paths = cfg.paths
    ctx.cfg_path = str(Path(cfg_path).resolve())

    setup_rs_remd(cfg, ctx)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python -m src.methods.rs_remd.run_rsremd_setup_job <config.yaml>")
    main(sys.argv[1])
