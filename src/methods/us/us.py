# src/methods/us.py
import subprocess
from pathlib import Path

import numpy as np

from src.config import Config
from src.methods import JobContext
from src.methods.base_method import BaseMethod


class USMethod(BaseMethod):

    def launch(self, cfg: Config, ctx: JobContext) -> None:
        print(f"\033[92m[US] setting up parameters\033[0m")
        job_id: str = f"{cfg.system.name}_{cfg.tag}_us"

        input_dir = ctx.paths["us"]["input"]
        script_dir = ctx.paths["us"]["script"]
        slurm_dir = ctx.paths["us"]["slurm"]
        amber_dir = ctx.paths["us"]["amber"]
        result_dir = ctx.paths["us"]["root"]

        exclude_arg = f"--exclude={','.join(cfg.cluster.exclude_ranks)}"

        pull_dir = self._get_pull_dir(ctx)

        ctx.us_job_id = {}

        for interval in cfg.methods.us.us_intervals:
            w_start = float(f"{float(interval.start):.2f}")
            w_end = float(f"{float(interval.end):.2f}")
            step = float(f"{float(interval.step):.2f}")

            for window in np.arange(w_start, w_end + step, step):
                window = float(f"{float(window):.2f}")
                dependency_job_id = self._resolve_pull_dependency(window, pull_dir, ctx)

                print(f"\033[92m[US] submit us window {window}\033[0m")
                us_cmd = [
                    "sbatch",
                    f"--job-name={job_id}_{window}",
                ]

                if dependency_job_id is not None:
                    us_cmd.append(f"--dependency=afterok:{dependency_job_id}")

                us_cmd += [
                    "--gres=gpu:1",
                    "--nodes=1",
                    "--time=2-00:00:00",
                    "--ntasks=1",
                    "--cpus-per-task=1",
                    exclude_arg,
                    f"--output={slurm_dir.resolve()}/slurm-%j_us{window}.out",
                    f"{script_dir.resolve()}/run_us.sh",
                    f"{window}",
                    str(input_dir.resolve()),
                    str(amber_dir.resolve()),
                    str(ctx.paths["us"]["top"].resolve()),
                    str(pull_dir.resolve()),
                ]

                us_result = subprocess.run(
                    us_cmd,
                    check=True,
                    capture_output=True,
                    text=True,
                    cwd=result_dir.resolve(),
                )

                if us_result.returncode != 0:
                    print("STDOUT:\n", us_result.stdout)
                    print("STDERR:\n", us_result.stderr)
                    raise RuntimeError("sbatch failed")

                us_job_id = us_result.stdout.strip().split()[-1]
                ctx.us_job_id[window] = us_job_id


    def _resolve_pull_dependency(self, window: float, pull_amber_dir: Path, ctx: JobContext) -> str | None:
        if ctx.pull_job_id is not None:
            pull_job_id = ctx.pull_job_id.get(window)
            if pull_job_id is not None and self._is_slurm_job_active(pull_job_id):
                return pull_job_id

        pull_restart = pull_amber_dir / f"restrt5.w{window}"
        if pull_restart.exists():
            return None

        raise RuntimeError(
            f"Pull output for window {window} not available. "
            f"Expected either an active pull job id or restart file {pull_restart}."
        )

    def _is_slurm_job_active(self, job_id: str) -> bool:
        try:
            result = subprocess.run(
                ["squeue", "-h", "-j", job_id],
                check=False,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError:
            return False

        return bool(result.stdout.strip())

    def _get_pull_dir(self, ctx: JobContext) -> Path:
        if ctx.paths.get("pull") is not None:
            pull_dir = ctx.paths["pull"]["amber"]
            if not pull_dir.exists():
                raise RuntimeError("Pull amber directory specified in yaml file does not exist.")
            return pull_dir
        else:
            us_path = ctx.paths["us"]["amber"]
            pull_dir = us_path.parent.parent / "pull" / "amber"
            if not pull_dir.exists():
                raise RuntimeError(f"Pull amber directory at expected location does not exist. ({pull_dir})")
            return pull_dir
