# src/methods/us.py
from src.methods import JobContext
from src.methods.base_method import BaseMethod
# from src.utils.shell import run
from pathlib import Path
from src.config import Config
import subprocess
import numpy as np


class PullMethod(BaseMethod):

    def launch(self, cfg: Config, ctx: JobContext) -> str:
        print(f"\033[92m[PULL] setting up parameters\033[0m")
        job_id: str = str(cfg.system.name) + "_" + str(cfg.tag) + "_pull"

        input_dir = ctx.paths["pull"]["input"]
        script_dir = ctx.paths["pull"]["script"]  # .resolve()
        slurm_dir = ctx.paths["pull"]["slurm"]
        amber_dir = ctx.paths["pull"]["amber"]
        result_dir = ctx.paths["pull"]["root"]
        # TODO: adjust handling of eq dir: where exactly is the input stored in general?; or remove here
        # eq_dir = cfg.paths["eq_dir"].resolve()

        exclude_arg = f"--exclude={','.join(cfg.cluster.exclude_ranks)}"

        last_job_id = None
        # TODO: adjust this so that we write window and id pairs in here
        ctx.job_ids.setdefault("pull", [])

        for interval in cfg.methods.pull.pull_intervals:
            w_start = float(f"{float(interval.start):.2f}")
            w_end = float(f"{float(interval.end):.2f}")
            step = float(f"{float(interval.step):.2f}")

            for window in np.arange(w_start, w_end + step, step):

                print(f"\033[92m[PULL] submit pull window {window} \033[0m")

                pull_cmd = [
                    "sbatch",
                    f"--job-name={job_id}_pull{window}",
                ]

                if last_job_id is not None:
                    pull_cmd.append(f"--dependency=afterok:{last_job_id}")
                elif ctx.eq_job_id is not None:
                    pull_cmd.append(f"--dependency=afterok:{ctx.eq_job_id}")

                pull_cmd += [
                    f"--gres=gpu:1",
                    f"--nodes=1",
                    f"--time=1-00:00:00",
                    f"--ntasks=1",
                    f"--cpus-per-task=1",
                    exclude_arg,
                    f"--output={slurm_dir.resolve()}/slurm-%j_pull{window}.out",
                    f"{script_dir.resolve()}/run_pull.sh",
                    "4",
                    f"{window}",
                    str(input_dir.resolve()),
                    str(amber_dir.resolve()),
                    str(ctx.paths["top"].resolve()),
                    str(cfg.us[0].replica_scaling),
                    str(ctx.paths["eq"]["root"].resolve()),
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

                # TODO: adjust some stuff here for correct writing
                pull_job_id = pull_result.stdout.strip().split()[-1]
                ctx.job_ids["pull"].append(pull_job_id)
                last_job_id = pull_job_id

        return last_job_id
