import subprocess
import shlex
import sys
from pathlib import Path

from src.methods.JobContext import JobContext
from src.methods.base_method import BaseMethod
from src.utils.check_eq_exists import check_eq_exists


class RSREMDMethod(BaseMethod):

    def launch(self, ctx: JobContext) -> None:

        self._submit_eq_simulation(ctx)
        self._submit_setup_job(ctx)
        self._submit_prod_simulation(ctx)


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
        dependency_arg = self._dependency_arg(ctx.setup_job_id, prev_job_id)
        if dependency_arg is not None:
            rsremd_eq.append(dependency_arg)

        rsremd_eq += [
            f"--gres=gpu:1",
            f"--nodes=1",
            f"--time=1-00:00:00",
            f"--ntasks=1",
            f"--cpus-per-task=1",
            exclude_arg,
            f"--output={slurm_dir.resolve()}/slurm-%j_rsremd_eq.out",
            f"{script_dir.resolve()}/run_rsremd_eq.sh",
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

        rsremd_eq_job_id = rsremd_eq_result.stdout.strip().split()[-1]
        ctx.rsremd_eq_job_id = rsremd_eq_job_id

    def _submit_setup_job(self, ctx: JobContext) -> None:
        if ctx.cfg_path is None:
            raise ValueError("ctx.cfg_path is required to submit the RS-REMD setup job.")
        if ctx.rsremd_eq_job_id is None:
            raise ValueError("ctx.rsremd_eq_job_id is required before submitting the RS-REMD setup job.")

        project_root = Path(__file__).resolve().parents[3]
        python_exe = Path(sys.executable).resolve()
        slurm_dir = ctx.paths["rs_remd"]["slurm"]
        result_dir = ctx.paths["rs_remd"]["root"]

        wrap_cmd = "cd {root} && {python} -m src.methods.rs_remd.run_rsremd_setup_job {cfg_path}".format(
            root=shlex.quote(str(project_root)),
            python=shlex.quote(str(python_exe)),
            cfg_path=shlex.quote(str(Path(ctx.cfg_path).resolve())),
        )

        rsremd_setup_cmd = [
            "sbatch",
            f"--job-name={self.cfg.system.name}_{self.cfg.tag}_rsremd_setup",
            f"--dependency=afterok:{ctx.rsremd_eq_job_id}",
            "--nodes=1",
            "--ntasks=1",
            "--cpus-per-task=1",
            "--time=00:30:00",
            f"--output={slurm_dir.resolve()}/slurm-%j_rsremd_setup.out",
            "--wrap",
            wrap_cmd,
        ]

        rsremd_setup_result = subprocess.run(
            rsremd_setup_cmd,
            check=True,
            capture_output=True,
            text=True,
            cwd=result_dir.resolve(),
        )

        if rsremd_setup_result.returncode != 0:
            print("STDOUT:\n", rsremd_setup_result.stdout)
            print("STDERR:\n", rsremd_setup_result.stderr)
            raise RuntimeError("sbatch failed")

        ctx.rsremd_setup_job_id = rsremd_setup_result.stdout.strip().split()[-1]

    def _submit_prod_simulation(self, ctx: JobContext):
        job_id = str(self.cfg.system.name) + "_" + str(self.cfg.tag)

        prev_job_id = ctx.rsremd_setup_job_id if ctx.rsremd_setup_job_id is not None else None

        script_dir = ctx.paths["rs_remd"]["script"]
        result_dir = ctx.paths["rs_remd"]["root"]
        log_dir = result_dir / "log"
        log_dir.mkdir(parents=True, exist_ok=True)
        slurm_dir = ctx.paths["rs_remd"]["slurm"]
        input_dir = ctx.paths["rs_remd"]["input"]
        exclude_arg = f"--exclude={','.join(self.cfg.cluster.exclude_ranks)}"

        rsremd_prod = [
            "sbatch",
            f"--job-name={job_id}_rsremd",
        ]
        if prev_job_id is not None:
            rsremd_prod.append(f"--dependency=afterok:{prev_job_id}")

        if self.cfg.methods.rs_remd.nodelist is not None:
            rsremd_prod.append(f"--nodelist={self.cfg.methods.rs_remd.nodelist}")

        if self.cfg.methods.rs_remd.partition is not None:
            rsremd_prod.append(f"--partition={self.cfg.methods.rs_remd.partition}")

        if self.cfg.methods.rs_remd.constraint is not None:
            rsremd_prod.append(f"--constraint={self.cfg.methods.rs_remd.constraint}")


        input_file = input_dir.resolve() / "rs_remd.groupfile"
        rsremd_prod += [
            f"--gres=gpu:{self.cfg.methods.rs_remd.ngpu}",
            f"--nodes=1",
            f"--time=2-00:00:00",
            f"--ntasks={self.cfg.methods.rs_remd.n_rep}",
            f"--cpus-per-task=1",
            exclude_arg,
            f"--output={slurm_dir.resolve()}/slurm-%j_rsremd.out",
            f"{script_dir.resolve()}/run_rsremd_prod.sh",
            str(self.cfg.methods.rs_remd.n_rep),
            str(input_file),
        ]

        rsremd_prod_result = subprocess.run(
            rsremd_prod,
            check=True,
            capture_output=True,
            text=True,
            cwd=log_dir.resolve(),
            # cwd=result_dir.resolve(),
        )

        if rsremd_prod_result.returncode != 0:
            print("STDOUT:\n", rsremd_prod_result.stdout)
            print("STDERR:\n", rsremd_prod_result.stderr)
            raise RuntimeError("sbatch failed")

        rsremd_prod_job_id = rsremd_prod_result.stdout.strip().split()[-1]
        ctx.rsremd_prod_job_id = rsremd_prod_job_id
