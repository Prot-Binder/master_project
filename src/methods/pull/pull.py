# src/methods/us.py
from src.methods import JobContext
from src.methods.base_method import BaseMethod
# from src.utils.shell import run
from pathlib import Path
from src.config import Config
import subprocess
import numpy as np

from src.utils.check_eq_exists import check_eq_exists


class PullMethod(BaseMethod):

    def launch(self, ctx: JobContext) -> None:
        print(f"\033[92m[PULL] setting up parameters\033[0m")
        job_id: str = str(self.cfg.system.name) + "_" + str(self.cfg.tag) + "_pull"

        # define paths
        input_dir = ctx.paths["pull"]["input"]
        script_dir = ctx.paths["pull"]["script"]  # .resolve()
        slurm_dir = ctx.paths["pull"]["slurm"]
        amber_dir = ctx.paths["pull"]["amber"]
        result_dir = ctx.paths["pull"]["root"]

        # define slurm arguments
        exclude_arg = f"--exclude={','.join(self.cfg.cluster.exclude_ranks)}"

        # check for dependency on equilibration job
        prev_job_id = ctx.eq_job_id if ctx.eq_job_id is not None else None
        if prev_job_id is None and (not check_eq_exists(ctx.paths["eq"]["input"])):
            raise RuntimeError("Equilibration output files not found. Please run equilibration before launching pull method.")

        ctx.pull_job_ids = {}
        initial_coordinate_file = ctx.paths["eq"]["input"] / "inpcrd_eq"
        stride = int(self.cfg.methods.pull.stride)
        mode = self.cfg.methods.pull.mode
        batch_start_coordinate_file = initial_coordinate_file

        for interval in self.cfg.methods.pull.pull_intervals:
            w_start = float(f"{float(interval.start):.2f}")
            w_end = float(f"{float(interval.end):.2f}")
            step = float(f"{float(interval.step):.2f}")

            windows = [float(f"{float(window):.2f}") for window in np.arange(w_start, w_end + step, step)]

            if mode == "parallel":
                for window_val in windows:
                    window_val = float(f"{float(window_val):.2f}")
                    window_str = f"{window_val:.2f}"

                    print(
                        f"\033[92m[PULL] submit pull window {window_val} "
                        f"(parallel, input: {initial_coordinate_file})\033[0m"
                    )

                    pull_cmd = [
                        "sbatch",
                        f"--job-name={job_id}_{window_val}",
                    ]

                    dependency_arg = self._dependency_arg(ctx.setup_job_id, ctx.eq_job_id)
                    if dependency_arg is not None:
                        pull_cmd.append(dependency_arg)

                    pull_cmd += [
                        f"--gres=gpu:1",
                        f"--nodes=1",
                        f"--time=1-00:00:00",
                        f"--ntasks=1",
                        f"--cpus-per-task=1",
                        exclude_arg,
                        f"--output={slurm_dir.resolve()}/slurm-%j_pull{window_val}.out",
                        f"{script_dir.resolve()}/run_pull.sh",
                        f"{window_str}",
                        str(input_dir.resolve()),
                        str(amber_dir.resolve()),
                        str(ctx.paths["pull"]["top"].resolve()),
                        str(initial_coordinate_file.resolve()),
                    ]

                    pull_result = subprocess.run(
                        pull_cmd,
                        capture_output=True,
                        text=True,
                        cwd=result_dir.resolve(),
                    )

                    if pull_result.returncode != 0:
                        print("STDOUT:\n", pull_result.stdout)
                        print("STDERR:\n", pull_result.stderr)
                        raise RuntimeError("sbatch failed")

                    pull_job_id = pull_result.stdout.strip().split()[-1]
                    ctx.pull_job_ids[window_val] = pull_job_id

                continue

            for batch_start in range(0, len(windows), stride):
                batch_windows = windows[batch_start:batch_start + stride]
                batch_dependency_job_id = prev_job_id
                batch_input_coordinate_file = batch_start_coordinate_file

                for window_val in batch_windows:
                    window_val = float(f"{float(window_val):.2f}")
                    window_str = f"{window_val:.2f}"

                    print(
                        f"\033[92m[PULL] submit pull window {window_val} "
                        f"(batch input: {batch_input_coordinate_file})\033[0m"
                    )

                    pull_cmd = [
                        "sbatch",
                        f"--job-name={job_id}_{window_val}",
                    ]

                    dependency_arg = self._dependency_arg(ctx.setup_job_id, batch_dependency_job_id)
                    if dependency_arg is not None:
                        pull_cmd.append(dependency_arg)

                    pull_cmd += [
                        f"--gres=gpu:1",
                        f"--nodes=1",
                        f"--time=1-00:00:00",
                        f"--ntasks=1",
                        f"--cpus-per-task=1",
                        exclude_arg,
                        f"--output={slurm_dir.resolve()}/slurm-%j_pull{window_val}.out",
                        f"{script_dir.resolve()}/run_pull.sh",
                        f"{window_str}",
                        str(input_dir.resolve()),
                        str(amber_dir.resolve()),
                        str(ctx.paths["pull"]["top"].resolve()),
                        str(Path(batch_input_coordinate_file).resolve()),
                    ]

                    pull_result = subprocess.run(
                        pull_cmd,
                        capture_output=True,
                        text=True,
                        cwd=result_dir.resolve(),
                    )

                    if pull_result.returncode != 0:
                        print("STDOUT:\n", pull_result.stdout)
                        print("STDERR:\n", pull_result.stderr)
                        raise RuntimeError("sbatch failed")

                    pull_job_id = pull_result.stdout.strip().split()[-1]
                    ctx.pull_job_ids[window_val] = pull_job_id
                    prev_job_id = pull_job_id

                last_window_in_batch = batch_windows[-1]
                batch_start_coordinate_file = amber_dir / f"restrt5.w{last_window_in_batch:.2f}"
