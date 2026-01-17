# src/methods/us.py
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

    def launch(self, cfg: Config):
        print("executing launch function of USMethod")
        self.launch2(cfg)

    
    def launch2(self, cfg: Config):
        print(f"\033[92m[US] setting up parameters\033[0m")
        job_id : str = str(cfg.us.replica_scaling) + "_" + str(cfg.system.name)
        
        input_dir = cfg.paths["results_root"] / "input"
        script_dir = cfg.paths["script_root"].resolve()

        eq_job_id = None

        # define output dirs and create them
        # slurm, amber output, pmd
        pmd_dir = cfg.paths["output_dir"] / "pmd"
        pmd_dir.mkdir(parents=True, exist_ok=True)
        slurm_dir = cfg.paths["output_dir"] / "slurm"
        slurm_dir.mkdir(parents=True, exist_ok=True)
        amber_dir = cfg.paths["output_dir"] / "amber"
        amber_dir.mkdir(parents=True, exist_ok=True)

        result_dir = cfg.paths["output_dir"]

        w_start = cfg.us.start
        w_end = cfg.us.end
        step = cfg.us.step

        exclude_arg = f"--exclude={','.join(cfg.cluster.exclude_ranks)}"

        # TODO: adjust handling of eq dir: where exactly is the input stored in general?
        eq_dir = cfg.paths["eq_dir"].resolve()
        print(eq_dir)
        print("slurm_dir:" + str(slurm_dir))
       
        for window in np.arange(w_start, w_end + step, step):

            print(f"\033[92m[US] submit pull window {window} \033[0m")
            pull_cmd = [
                "sbatch",
                f"--job-name={job_id}_pull{window}",
                f"--gres=gpu:1",
                f"--nodes=1",
                f"--time=1-00:00:00",
                f"--ntasks=1",
                f"--cpus-per-task=1",
                exclude_arg,
                f"--output={slurm_dir}/slurm-%j_pull{window}.out",
                f"{script_dir}/run_pull.sh",
                "4",
                f"{window}",
                str(input_dir.resolve()),
                str(amber_dir.resolve()),
                str(cfg.paths["top_dir"].resolve()),
                str(cfg.us.replica_scaling),
                str(cfg.paths["eq_dir"].resolve()),
            ]

            if not(eq_job_id is None) :
                pull_cmd.append(f"--dependency=afterok:{eq_job_id}")

            # TODO: execute this from result directory
            pull_result = subprocess.run(
                pull_cmd,
                check=True,
                capture_output=True,
                text=True,
                cwd=result_dir.resolve(),
            )

            if pull_result.returncode != 0:
                print("STDOUT:\n", res.stdout)
                print("STDERR:\n", res.stderr)
                raise RuntimeError("sbatch failed")

            pull_job_id = pull_result.stdout.strip().split()[-1]

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
                f"--output={slurm_dir}/slurm-%j_us{window}.out",
                f"{script_dir}/run_us.sh",
                f"{window}",
                str(input_dir.resolve()),
                str(amber_dir.resolve()),
                str(cfg.paths["top_dir"].resolve()),
                str(cfg.us.replica_scaling),
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
                print("STDOUT:\n", res.stdout)
                print("STDERR:\n", res.stderr)
                raise RuntimeError("sbatch failed")

            us_job_id = us_result.stdout.strip().split()[-1]

