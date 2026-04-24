import subprocess
from pathlib import Path

import numpy as np

from src.config import resolve_continuation_restart_file
from src.methods import JobContext
from src.methods.base_method import BaseMethod


class USMethod(BaseMethod):

    def launch(self, ctx: JobContext) -> None:
        print(f"\033[92m[US] setting up parameters\033[0m")
        job_id: str = f"{self.cfg.system.name}_{self.cfg.tag}_us"

        input_dir = ctx.paths["us"]["input"]
        script_dir = ctx.paths["us"]["script"]
        slurm_dir = ctx.paths["us"]["slurm"]
        amber_dir = ctx.paths["us"]["amber"]
        result_dir = ctx.paths["us"]["root"]

        exclude_arg = f"--exclude={','.join(self.cfg.cluster.exclude_ranks)}"

        continuation_enabled = self._is_continuation_enabled()
        pull_dir = None if continuation_enabled else self._get_pull_dir(ctx)

        ctx.us_job_ids = {}

        for interval in self.cfg.methods.us.us_intervals:
            w_start = float(f"{float(interval.start):.2f}")
            w_end = float(f"{float(interval.end):.2f}")
            step = float(f"{float(interval.step):.2f}")

            windows = [float(f"{float(window):.2f}") for window in np.arange(w_start, w_end + step, step)]

            for window in windows:
                window_value = float(f"{float(window):.2f}")
                window_str = f"{window_value:.2f}"
                coordinate_file = self._resolve_input_coordinate(window_value, pull_dir)
                dependency_job_id = None
                if not continuation_enabled:
                    dependency_job_id = self._resolve_pull_dependency(window_value, pull_dir, ctx)

                print(f"\033[92m[US] submit us window {window_str}\033[0m")
                us_cmd = [
                    "sbatch",
                    f"--job-name={job_id}_{window_str}",
                ]

                dependency_arg = self._dependency_arg(ctx.setup_job_id, dependency_job_id)
                if dependency_arg is not None:
                    us_cmd.append(dependency_arg)

                us_cmd += [
                    "--gres=gpu:1",
                    "--nodes=1",
                    "--time=2-00:00:00",
                    "--ntasks=1",
                    "--cpus-per-task=1",
                    exclude_arg,
                    f"--output={slurm_dir.resolve()}/slurm-%j_us{window_str}.out",
                    f"{script_dir.resolve()}/run_us.sh",
                    f"{window_str}",
                    str(input_dir.resolve()),
                    str(amber_dir.resolve()),
                    str(ctx.paths["us"]["top"].resolve()),
                    str(coordinate_file.resolve()),
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
                ctx.us_job_ids[window] = us_job_id


    def _is_continuation_enabled(self) -> bool:
        us_cfg = self.cfg.methods.us
        return us_cfg is not None and us_cfg.continuation is not None and us_cfg.continuation.enabled

    def _resolve_input_coordinate(self, window: float, pull_amber_dir: Path | None) -> Path:
        window_val = float(f"{float(window):.2f}")
        window_str = f"{window_val:.2f}"
        if self._is_continuation_enabled():
            coord_file = resolve_continuation_restart_file(
                self.cfg,
                self.cfg.methods.us.continuation,
                current_method="us",
                window=window_str,
            )
            if not coord_file.exists():
                raise FileNotFoundError(
                    f"US input coordinate file does not exist for window {window_str}: {coord_file}"
                )
        else:
            if pull_amber_dir is None:
                raise RuntimeError("Internal error: pull_amber_dir is required when US continuation is disabled.")
            coord_file = pull_amber_dir / f"restrt5.w{window_str}"

        return coord_file

    def _resolve_pull_dependency(self, window: float, pull_amber_dir: Path | None, ctx: JobContext) -> str | None:
        if pull_amber_dir is None:
            raise RuntimeError("Internal error: pull_amber_dir is required for pull dependency resolution.")

        window_val = float(f"{float(window):.2f}")
        window_str = f"{window_val:.2f}"
        if ctx.pull_job_ids is not None:
            pull_job_id = ctx.pull_job_ids.get(window_val)
            if pull_job_id is not None and self._is_slurm_job_active(pull_job_id):
                return pull_job_id

        pull_restart = pull_amber_dir / f"restrt5.w{window_str}"
        if pull_restart.exists():
            return None

        raise RuntimeError(
            f"Pull output for window {window_str} not available. "
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
