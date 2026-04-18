import subprocess
from pathlib import Path

import numpy as np

from src.methods.JobContext import JobContext
from src.methods.base_method import BaseMethod


def _interval_windows(start: float, end: float, step: float) -> list[float]:
    windows = []
    for window in np.arange(start, end + step, step):
        windows.append(float(f"{float(window):.2f}"))
    return windows


def _collect_pull_dependencies(ctx: JobContext, windows: list[float]) -> list[str]:
    dependency_ids: list[str] = []
    pull_amber_dir = ctx.paths["pull"]["amber"]

    for window in windows:
        pull_job_id = None
        if ctx.pull_job_ids is not None:
            pull_job_id = ctx.pull_job_ids.get(window)

        if pull_job_id is None:
            restart_file = pull_amber_dir / f"restrt5.w{window:.2f}"
            if not restart_file.exists():
                raise RuntimeError(
                    f"Missing pull restart file for window {window:.2f}: {restart_file}. "
                    "Run the referenced pull method first or keep its job ids in ctx.pull_job_ids."
                )
            continue

        if pull_job_id is not None and pull_job_id not in dependency_ids:
            dependency_ids.append(pull_job_id)

    return dependency_ids


class USREMDMethod(BaseMethod):

    def launch(self, ctx: JobContext) -> None:
        if self.cfg.methods.us_remd is None:
            raise ValueError("USREMDMethod.launch() requires cfg.methods.us_remd to be configured.")

        method_cfg = self.cfg.methods.us_remd

        script_dir = ctx.paths["us_remd"]["script"]
        result_dir = ctx.paths["us_remd"]["root"]
        slurm_dir = ctx.paths["us_remd"]["slurm"]
        input_dir = ctx.paths["us_remd"]["input"]
        exclude_arg = f"--exclude={','.join(self.cfg.cluster.exclude_ranks)}"

        ctx.us_remd_job_ids = {}

        for block_idx, interval in enumerate(method_cfg.us_remd_intervals):
            windows = _interval_windows(interval.start, interval.end, interval.step)
            dependency_ids = _collect_pull_dependencies(ctx, windows)

            n_windows = len(windows)
            block_dir = result_dir / f"log_block_{block_idx}"
            block_dir.mkdir(parents=True, exist_ok=True)

            groupfile = input_dir.resolve() / f"us_remd_block{block_idx}.groupfile"
            # if not groupfile.exists():
            #     raise FileNotFoundError(
            #         f"US-REMD groupfile not found: {groupfile}. "
            #         "Create it before launching the us_remd method."
            #     )

            usremd_cmd = [
                "sbatch",
                f"--job-name={self.cfg.system.name}_{self.cfg.tag}_usremd_b{block_idx}",
            ]
            dependency_arg = self._dependency_arg(ctx.setup_job_id, dependency_ids)
            if dependency_arg is not None:
                usremd_cmd.append(dependency_arg)
            if method_cfg.partition is not None:
                usremd_cmd.append(f"--partition={method_cfg.partition}")
            if method_cfg.constraint is not None:
                usremd_cmd.append(f"--constraint={method_cfg.constraint}")

            usremd_cmd += [
                f"--gres=gpu:{method_cfg.ngpu}",
                "--nodes=1",
                "--time=2-00:00:00",
                f"--ntasks={n_windows}",
                "--cpus-per-task=1",
                "--mem=24G",
                exclude_arg,
                f"--output={slurm_dir.resolve()}/slurm-%j_usremd_b{block_idx}.out",
                f"{script_dir.resolve()}/run_usremd_prod.sh",
                str(n_windows),
                str(groupfile),
            ]

            result = subprocess.run(
                usremd_cmd,
                check=True,
                capture_output=True,
                text=True,
                cwd=block_dir.resolve(),
            )

            if result.returncode != 0:
                print("STDOUT:\n", result.stdout)
                print("STDERR:\n", result.stderr)
                raise RuntimeError("sbatch failed")

            ctx.us_remd_job_ids[block_idx] = result.stdout.strip().split()[-1]
