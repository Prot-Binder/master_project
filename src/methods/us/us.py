# src/methods/us.py
from src.methods import JobContext
from src.methods.base_method import BaseMethod
# from src.utils.shell import run
from pathlib import Path
from src.config import Config
import subprocess
import numpy as np

class USMethod(BaseMethod):
    def prepare(self, run_dir):
        # generate replicas, mdin, restraints
        pass
    
    def launch(self, cfg: Config, ctx: JobContext) -> str:
        print(f"\033[92m[US] setting up parameters\033[0m")
        job_id : str = str(cfg.us[0].replica_scaling) + "_" + str(cfg.system.name)

        input_dir = ctx.paths["us"]["input"]
        script_dir = ctx.paths["us"]["script"] # .resolve()
        slurm_dir = ctx.paths["us"]["slurm"]
        amber_dir = ctx.paths["us"]["amber"]
        result_dir = ctx.paths["us"]["root"]
        # TODO: adjust handling of eq dir: where exactly is the input stored in general?; or remove here
        # eq_dir = cfg.paths["eq_dir"].resolve()


        exclude_arg = f"--exclude={','.join(cfg.cluster.exclude_ranks)}"

        last_us_job_id = None
        ctx.job_ids.setdefault("pull", [])
        ctx.job_ids.setdefault("us", [])

        for us_item in cfg.us:
            w_start = us_item.start
            w_end = us_item.end
            step = us_item.step

            for window in np.arange(w_start, w_end + step, step):

                print(f"\033[92m[US] submit pull window {window} \033[0m")

                pull_cmd = [
                    "sbatch",
                    f"--job-name={job_id}_pull{window}",
                ]

                if ctx.eq_job_id is not None:
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

                # TODO: execute this from result directory
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
                ctx.job_ids["pull"].append(pull_job_id)

                print(f"\033[92m[US] submit us window {window}\033[0m")
                us_cmd = [
                    "sbatch",
                    f"--dependency=afterok:{pull_job_id}",
                    f"--job-name={job_id}_us{window}",
                    "--gres=gpu:1",
                    "--nodes=1",
                    "--time=1-00:00:00",
                    "--ntasks=1",
                    "--cpus-per-task=1",
                    exclude_arg,
                    f"--output={slurm_dir.resolve()}/slurm-%j_us{window}.out",
                    f"{script_dir.resolve()}/run_us.sh",
                    f"{window}",
                    str(input_dir.resolve()),
                    str(amber_dir.resolve()),
                    str(ctx.paths["top"].resolve()),
                    str(cfg.us[0].replica_scaling),
                ]

                # TODO: execute this from result directory
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
                ctx.job_ids["us"].append(us_job_id)
                last_us_job_id = us_job_id

        return last_us_job_id
