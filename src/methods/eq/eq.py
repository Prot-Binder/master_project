# src/methods/rs_remd.py
from src.methods.JobContext import JobContext
from src.methods.base_method import BaseMethod
from src.config import Config
import subprocess


# from src.utils.shell import run

class EqMethod(BaseMethod):
    def prepare(self, run_dir):
        # generate replicas, mdin, restraints
        pass

    def launch(self, cfg: Config, ctx: JobContext) -> str:

        job_id : str = str(cfg.us[0].replica_scaling) + "_" + str(cfg.system.name)

        script_dir = ctx.paths["eq"]["script"]
        eq_dir = ctx.paths["eq"]["root"]
        slurm_dir = ctx.paths["eq"]["slurm"]
        output_dir = ctx.paths["eq"]["amber"]
        input_dir = ctx.paths["eq"]["input"]
        exclude_arg = f"--exclude={','.join(cfg.cluster.exclude_ranks)}"
        

        eq_cmd = [
                    "sbatch",
                    f"--job-name={job_id}_eq",
                    f"--gres=gpu:1",
                    f"--nodes=1",
                    f"--time=1-00:00:00",
                    f"--ntasks=1",
                    f"--cpus-per-task=1",
                    exclude_arg,
                    f"--output={slurm_dir.resolve()}/slurm-%j_eq.out",
                    f"{script_dir.resolve()}/run_eq.sh",
                    "0",
                    "4",
                    "1",
                    str(input_dir.resolve()),
                    str(output_dir.resolve()),
                    str(ctx.paths["top"].resolve()),
                    str(cfg.us[0].replica_scaling),
                    str(int(cfg.eq.use_cpu)),
                ]

        # TODO: execute this from result directory
        eq_result = subprocess.run(
            eq_cmd,
            check=True,
            capture_output=True,
            text=True,
            cwd=eq_dir.resolve(),
        )

        if eq_result.returncode != 0:
            print("STDOUT:\n", eq_result.stdout)
            print("STDERR:\n", eq_result.stderr)
            raise RuntimeError("sbatch failed")

        eq_job_id = eq_result.stdout.strip().split()[-1]
        ctx.eq_job_id = eq_job_id
        return eq_job_id
