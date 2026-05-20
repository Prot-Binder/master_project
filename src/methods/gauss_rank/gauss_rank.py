"""gauss_rank workflow launcher."""

from __future__ import annotations

import subprocess

from src.methods.JobContext import JobContext
from src.methods.base_method import BaseMethod


class GaussRankMethod(BaseMethod):
    def launch(self, ctx: JobContext) -> None:
        method_cfg = self.cfg.methods.gauss_rank
        if method_cfg is None:
            raise ValueError("GaussRankMethod.launch() requires cfg.methods.gauss_rank to be configured.")

        method_paths = ctx.paths["gauss_rank"]
        top_file = method_paths["top"] / "prmtop1"
        # if not top_file.exists():
        #     raise FileNotFoundError(f"gauss_rank topology file not found: {top_file}")

        ctx.gauss_rank_job_ids = {}
        exclude_arg = f"--exclude={','.join(self.cfg.cluster.exclude_ranks)}"
        ref_file = method_paths["setup"] / "system.rst"
        # if not ref_file.exists():
        #     raise FileNotFoundError(f"gauss_rank reference file not found: {ref_file}")

        amber_dir = method_paths["amber"]
        # if not amber_dir.exists():
        #     raise FileNotFoundError(f"gauss_rank amber output directory not found: {amber_dir}")

        input_coord = ctx.paths["eq"]["input"] / "inpcrd_eq"
        needs_eq_dependency = not input_coord.exists() and ctx.eq_job_id is not None
        # if not input_coord.exists() and not needs_eq_dependency:
        #     raise FileNotFoundError(f"gauss_rank input restart file not found: {input_coord}")

        for replicate_idx in range(method_cfg.n_reps):
            mdin_path = method_paths["input"] / f"mdin_rep{replicate_idx}"
            # if not mdin_path.exists():
            #     raise FileNotFoundError(f"gauss_rank mdin file not found for replicate {replicate_idx}: {mdin_path}")

            job_name = f"{self.cfg.system.name}_{self.cfg.tag}_gauss_rank_r{replicate_idx}"
            sbatch_cmd = [
                "sbatch",
                f"--job-name={job_name}",
            ]
            dependency_arg = self._dependency_arg(
                ctx.setup_job_id,
                ctx.eq_job_id if needs_eq_dependency else None,
            )
            if dependency_arg is not None:
                sbatch_cmd.append(dependency_arg)

            sbatch_cmd += [
                "--gres=gpu:1",
                "--nodes=1",
                "--time=2-00:00:00",
                "--ntasks=1",
                "--cpus-per-task=1",
                exclude_arg,
                f"--output={method_paths['slurm'].resolve()}/slurm-%j_gauss_rank_r{replicate_idx}.out",
                f"{method_paths['script'].resolve()}/run_gauss_rank.sh",
                str(mdin_path.resolve()),
                str(amber_dir.resolve()),
                str(top_file.resolve()),
                str(input_coord.resolve()),
                str(ref_file.resolve()),
                str(replicate_idx),
            ]

            result = subprocess.run(
                sbatch_cmd,
                capture_output=True,
                text=True,
                cwd=method_paths["root"].resolve(),
            )
            if result.returncode != 0:
                print("STDOUT:\n", result.stdout)
                print("STDERR:\n", result.stderr)
                raise RuntimeError("sbatch failed")

            ctx.gauss_rank_job_ids[replicate_idx] = result.stdout.strip().split()[-1]
