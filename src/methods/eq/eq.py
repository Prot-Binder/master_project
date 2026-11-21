from src.methods.JobContext import JobContext
from src.methods.base_method import BaseMethod
from src.config import Config
import shutil
import subprocess

class EqMethod(BaseMethod):

    def launch(self, ctx: JobContext) -> None:
        if self.cfg.methods.eq is None:
            raise ValueError("EqMethod.launch() requires cfg.methods.eq to be configured.")

        input_restart = self.cfg.methods.eq.input_restart
        if input_restart is not None:
            # Reuse an existing (shared) equilibrated structure instead of running equilibration.
            target = ctx.paths["eq"]["input"] / "inpcrd_eq"
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(input_restart, target)
            print(f"\033[92m[EQ] skipped equilibration; using {input_restart} as {target}\033[0m")
            ctx.eq_job_id = None
            return

        job_id = str(self.cfg.system.name) + "_" + str(self.cfg.tag)

        script_dir = ctx.paths["eq"]["script"]
        eq_dir = ctx.paths["eq"]["root"]
        slurm_dir = ctx.paths["eq"]["slurm"]
        output_dir = ctx.paths["eq"]["amber"]
        input_dir = ctx.paths["eq"]["input"]
        exclude_arg = f"--exclude={','.join(self.cfg.cluster.exclude_ranks)}"
        

        eq_cmd = [
                    "sbatch",
                    f"--job-name={job_id}_eq",
        ]
        if ctx.setup_job_id is not None:
            eq_cmd.append(f"--dependency=afterok:{ctx.setup_job_id}")

        eq_cmd += [
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
                    str(ctx.paths["eq"]["top"].resolve()),
                    str(int(self.cfg.methods.eq.use_cpu)),
                    str(int(self.cfg.methods.eq.nstlim_eq is not None)),
                ]

        eq_result = subprocess.run(
            eq_cmd,
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
