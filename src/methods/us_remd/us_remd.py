import subprocess

from src.methods.JobContext import JobContext
from src.methods.base_method import BaseMethod
from src.config import resolve_scheduler_nodes, us_remd_interval_windows


def _collect_pull_dependencies(cfg, ctx: JobContext, windows: list[float]) -> list[str]:
    dependency_ids: list[str] = []
    pull_amber_dir = ctx.paths["pull"]["amber"]
    us_remd_cfg = cfg.methods.us_remd

    if us_remd_cfg is None:
        raise ValueError("_collect_pull_dependencies() requires cfg.methods.us_remd to be configured.")

    if us_remd_cfg.continuation is not None and us_remd_cfg.continuation.enabled:
        return []

    for window in windows:
        pull_job_id = None
        if ctx.pull_job_ids is not None:
            pull_job_id = ctx.pull_job_ids.get(window)

        if pull_job_id is None:
            restart_file = pull_amber_dir / f"restrt5.w{window:.2f}"
            if not restart_file.exists():
                raise RuntimeError(
                    f"Missing pull restart file for window {window:.2f}: {restart_file}. "
                    "Run the referenced pull method first or keep its job ids in ctx.pull_job_ids."
                )
            continue

        if pull_job_id is not None and pull_job_id not in dependency_ids:
            dependency_ids.append(pull_job_id)

    return dependency_ids


class USREMDMethod(BaseMethod):

    def launch(self, ctx: JobContext) -> None:
        if self.cfg.methods.us_remd is None:
            raise ValueError("USREMDMethod.launch() requires cfg.methods.us_remd to be configured.")

        method_cfg = self.cfg.methods.us_remd
        requested_nodes = resolve_scheduler_nodes(
            nodelist=method_cfg.nodelist,
            nodes=method_cfg.nodes,
        )

        script_dir = ctx.paths["us_remd"]["script"]
        result_dir = ctx.paths["us_remd"]["root"]
        slurm_dir = ctx.paths["us_remd"]["slurm"]
        input_dir = ctx.paths["us_remd"]["input"]
        exclude_arg = f"--exclude={','.join(self.cfg.cluster.exclude_ranks)}"

        ctx.us_remd_job_ids = {}

        for block_idx, interval in enumerate(method_cfg.us_remd_intervals):
            windows = us_remd_interval_windows(interval)
            dependency_ids = _collect_pull_dependencies(self.cfg, ctx, windows)

            n_windows = len(windows)
            block_dir = result_dir / f"log_block_{block_idx}"
            block_dir.mkdir(parents=True, exist_ok=True)

            groupfile = input_dir.resolve() / f"us_remd_block{block_idx}.groupfile"
            # if not groupfile.exists():
            #     raise FileNotFoundError(
            #         f"US-REMD groupfile not found: {groupfile}. "
            #         "Create it before launching the us_remd method."
            #     )

            usremd_cmd = [
                "sbatch",
                f"--job-name={self.cfg.system.name}_{self.cfg.tag}_usremd_b{block_idx}",
            ]
            dependency_arg = self._dependency_arg(ctx.setup_job_id, dependency_ids)
            if dependency_arg is not None:
                usremd_cmd.append(dependency_arg)
            if method_cfg.nodelist is not None:
                usremd_cmd.append(f"--nodelist={method_cfg.nodelist}")
            if method_cfg.partition is not None:
                usremd_cmd.append(f"--partition={method_cfg.partition}")
            if method_cfg.constraint is not None:
                usremd_cmd.append(f"--constraint={method_cfg.constraint}")
            if method_cfg.ntasks_per_node is not None:
                usremd_cmd.append(f"--ntasks-per-node={method_cfg.ntasks_per_node}")

            usremd_cmd += [
                f"--gres=gpu:{method_cfg.ngpu}",
                f"--nodes={requested_nodes}",
                "--time=2-00:00:00",
                f"--ntasks={n_windows}",
                "--cpus-per-task=1",
                "--mem=80G",
                exclude_arg,
                f"--output={slurm_dir.resolve()}/slurm-%j_usremd_b{block_idx}.out",
                f"{script_dir.resolve()}/run_usremd_prod.sh",
                str(n_windows),
                str(groupfile),
            ]

            result = subprocess.run(
                usremd_cmd,
                capture_output=True,
                text=True,
                cwd=block_dir.resolve(),
            )

            if result.returncode != 0:
                print("STDOUT:\n", result.stdout)
                print("STDERR:\n", result.stderr)
                raise RuntimeError("sbatch failed")

            ctx.us_remd_job_ids[block_idx] = result.stdout.strip().split()[-1]
