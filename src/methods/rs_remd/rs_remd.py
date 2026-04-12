from src.methods.JobContext import JobContext
from src.methods.base_method import BaseMethod
import subprocess

from src.methods.rs_remd.rs_remd_setup import setup_rs_remd
from src.utils.check_eq_exists import check_eq_exists


class RSREMDMethod(BaseMethod):

    def launch(self, ctx: JobContext) -> None:

        self._submit_eq_simulation(ctx)
        setup_rs_remd(self.cfg, ctx)
        self._submit_prod_simulation()


    def _submit_eq_simulation(self, ctx: JobContext):
        job_id = str(self.cfg.system.name) + "_" + str(self.cfg.tag)

        prev_job_id = ctx.eq_job_id if ctx.eq_job_id is not None else None
        if prev_job_id is None and (not check_eq_exists(ctx.paths["eq"]["amber"])):
            raise RuntimeError(
                "Equilibration output files not found. Please run equilibration before launching pull method.")

        script_dir = ctx.paths["rs_remd"]["script"]
        # change
        result_dir = ctx.paths["rs_remd"]["root"]
        slurm_dir = ctx.paths["rs_remd"]["eq"]
        output_dir = ctx.paths["rs_remd"]["eq"]
        input_dir = ctx.paths["rs_remd"]["input"]
        exclude_arg = f"--exclude={','.join(self.cfg.cluster.exclude_ranks)}"

        rsremd_eq = [
            "sbatch",
            f"--job-name={job_id}_rsremd_eq",
        ]
        if ctx.setup_job_id is not None:
            rsremd_eq.append(f"--dependency=afterok:{ctx.setup_job_id}")

        rsremd_eq += [
            f"--gres=gpu:1",
            f"--nodes=1",
            f"--time=1-00:00:00",
            f"--ntasks=1",
            f"--cpus-per-task=1",
            exclude_arg,
            f"--output={slurm_dir.resolve()}/slurm-%j_rsremd_eq.out",
            f"{script_dir.resolve()}/rsremd_eq.sh",
            str(input_dir.resolve()),
            str(output_dir.resolve()),
            str(ctx.paths["rs_remd"]["top"].resolve()),
            str(ctx.paths["eq"]["input"].resolve()),
            str(self.cfg.methods.rs_remd.n_rep)
        ]

        rsremd_eq_result = subprocess.run(
            rsremd_eq,
            check=True,
            capture_output=True,
            text=True,
            cwd=result_dir.resolve(),
        )

        if rsremd_eq_result.returncode != 0:
            print("STDOUT:\n", rsremd_eq_result.stdout)
            print("STDERR:\n", rsremd_eq_result.stderr)
            raise RuntimeError("sbatch failed")

        rsremd_eq_result = rsremd_eq_result.stdout.strip().split()[-1]
        ctx.rsremd_eq_result = rsremd_eq_result

    def _submit_prod_simulation(self):
        pass
