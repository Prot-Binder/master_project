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
        if prev_job_id is None and (not check_eq_exists(ctx.paths["eq"]["amber"])):
            raise RuntimeError("Equilibration output files not found. Please run equilibration before launching pull method.")

        ctx.pull_job_ids = {}

        for interval in self.cfg.methods.pull.pull_intervals:
            w_start = float(f"{float(interval.start):.2f}")
            w_end = float(f"{float(interval.end):.2f}")
            step = float(f"{float(interval.step):.2f}")

            windows = [float(f"{float(window):.2f}") for window in np.arange(w_start, w_end + step, step)]

            for window_val in windows:
                window_val = float(f"{float(window_val):.2f}")
                window_str = f"{window_val:.2f}"

                print(f"\033[92m[PULL] submit pull window {window_val} \033[0m")

                pull_cmd = [
                    "sbatch",
                    f"--job-name={job_id}_{window_val}",
                ]

                if prev_job_id is not None:
                    pull_cmd.append(f"--dependency=afterok:{prev_job_id}")

                pull_cmd += [
                    f"--gres=gpu:1",
                    f"--nodes=1",
                    f"--time=1-00:00:00",
                    f"--ntasks=1",
                    f"--cpus-per-task=1",
                    exclude_arg,
                    f"--output={slurm_dir.resolve()}/slurm-%j_pull{window}.out",
                    f"{script_dir.resolve()}/run_pull.sh",
                    f"{window_str}",
                    str(input_dir.resolve()),
                    str(amber_dir.resolve()),
                    str(ctx.paths["pull"]["top"].resolve()),
                    str(ctx.paths["eq"]["input"].resolve()),
                ]

                pull_result = subprocess.run(
                    pull_cmd,
                    check=True,
                    capture_output=True,
                    text=True,
                    cwd=result_dir.resolve(),
                )

                if pull_result.returncode != 0:
                    print("STDOUT:\n", pull_result.stdout)
                    print("STDERR:\n", pull_result.stderr)
                    raise RuntimeError("sbatch failed")

                pull_job_id = pull_result.stdout.strip().split()[-1]
                prev_job_id = pull_job_id
                ctx.pull_job_ids[window_val] = pull_job_id
