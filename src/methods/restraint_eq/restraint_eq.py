from __future__ import annotations

import subprocess
from pathlib import Path

from src.methods import JobContext
from src.methods.base_method import BaseMethod
from src.setup.restraint_cases import (
    expand_restraint_cases,
    group_restraint_cases_by_class,
    rendered_restraint_filename,
    rendered_restraint_mdin_filename,
)


class RestraintEqLauncher(BaseMethod):
    REQUIRED_EQUILIBRATION_STAGES = ("min0.in", "min1.in", "heat.in", "npt.in")
    PREPARATION_STAGE = "pre.in"
    OPTIONAL_PRODUCTION_STAGE = "prod.in"

    def launch(self, ctx: JobContext) -> None:
        cases = expand_restraint_cases(self.cfg)
        if len(cases) == 0:
            return

        if self.cfg.restraints is None:
            raise ValueError("RestraintEqLauncher.launch() requires cfg.restraints to be configured.")

        print("\033[92m[RESTRAINT_EQ] setting up parameters\033[0m")
        exclude_arg = f"--exclude={','.join(self.cfg.cluster.exclude_ranks)}"
        contribution_cfgs = {contribution.name: contribution for contribution in self.cfg.restraints.contributions}
        script_path = Path(__file__).resolve().parent / "run_restraint_eq.sh"
        ctx.restraint_eq_job_ids = {}
        ctx.restraint_pre_job_ids = {}
        ctx.restraint_prod_job_ids = {}
        setup_is_pending = ctx.setup_job_id is not None

        for group in group_restraint_cases_by_class(self.cfg):
            class_eq_paths = ctx.paths["restraints"]["eq"][group.target_class]
            input_dir = class_eq_paths["input"]
            amber_dir = class_eq_paths["amber"]
            slurm_dir = class_eq_paths["slurm"]
            result_dir = class_eq_paths["root"]
            setup_dir = ctx.paths["restraints"]["setup"][group.target_class]

            stage_files = self._resolve_class_stage_files(
                input_dir,
                group.target_class,
                require_existing=not setup_is_pending,
            )
            prmtop = self._resolve_prmtop(setup_dir, group.target_class)
            initial_coord = setup_dir / "system.rst"
            reference_coord = setup_dir / "system.rst"

            if not setup_is_pending:
                self._require_existing_file(prmtop, f"restraint prmtop for class {group.target_class}")
                self._require_existing_file(initial_coord, f"restraint coordinate file for class {group.target_class}")
                self._require_existing_file(reference_coord, f"restraint reference coordinate file for class {group.target_class}")

            print(f"\033[92m[RESTRAINT_EQ] submit class {group.target_class}\033[0m")
            sbatch_cmd = [
                "sbatch",
                f"--job-name={self.cfg.system.name}_{self.cfg.tag}_{group.target_class}_restraint_eq",
            ]

            dependency_arg = self._dependency_arg(ctx.setup_job_id)
            if dependency_arg is not None:
                sbatch_cmd.append(dependency_arg)

            sbatch_cmd += [
                "--gres=gpu:1",
                "--nodes=1",
                "--ntasks=1",
                "--cpus-per-task=1",
                "--time=2-00:00:00",
                exclude_arg,
                f"--output={slurm_dir.resolve()}/slurm-%j_{group.target_class}.out",
                str(script_path.resolve()),
                str(amber_dir.resolve()),
                str(prmtop.resolve()),
                str(initial_coord.resolve()),
                str(reference_coord.resolve()),
                group.target_class,
            ]
            sbatch_cmd.extend(str(stage_file.resolve()) for stage_file in stage_files)

            result = subprocess.run(
                sbatch_cmd,
                check=True,
                capture_output=True,
                text=True,
                cwd=result_dir.resolve(),
            )

            if result.returncode != 0:
                print("STDOUT:\n", result.stdout)
                print("STDERR:\n", result.stderr)
                raise RuntimeError("sbatch failed")

            ctx.restraint_eq_job_ids[group.target_class] = result.stdout.strip().split()[-1]

        for case in cases:
            contribution_cfg = contribution_cfgs[case.contribution_name]
            contribution_paths = ctx.paths["restraints"]["contributions"][case.contribution_name]
            input_dir = contribution_paths["input"]
            amber_dir = contribution_paths["amber"]
            slurm_dir = contribution_paths["slurm"]
            result_dir = contribution_paths["root"]
            setup_dir = ctx.paths["restraints"]["setup"][case.target_class]
            class_eq_paths = ctx.paths["restraints"]["eq"][case.target_class]
            class_job_id = ctx.restraint_eq_job_ids.get(case.target_class)

            pre_mdin = input_dir / rendered_restraint_mdin_filename(
                self.PREPARATION_STAGE,
                case.contribution_name,
                case.kappa,
            )
            restraint_file = input_dir / rendered_restraint_filename(contribution_cfg.restraint_file, case.kappa)
            prmtop = self._resolve_prmtop(setup_dir, case.target_class)
            initial_coord = class_eq_paths["amber"] / f"{case.target_class}_npt.restrt"
            reference_coord = setup_dir / "system.rst"

            if not setup_is_pending:
                self._require_existing_file(pre_mdin, f"restraint pre mdin for case {case.case_name}")
                self._require_existing_file(restraint_file, f"rendered restraint file for case {case.case_name}")
                self._require_existing_file(prmtop, f"restraint prmtop for class {case.target_class}")
            if class_job_id is None:
                self._require_existing_file(initial_coord, f"class-equilibrated restraint coordinate for class {case.target_class}")
            if not setup_is_pending:
                self._require_existing_file(reference_coord, f"restraint reference coordinate file for class {case.target_class}")

            print(f"\033[92m[RESTRAINT_EQ] submit pre case {case.case_name}\033[0m")
            sbatch_cmd = [
                "sbatch",
                f"--job-name={self.cfg.system.name}_{self.cfg.tag}_{case.case_name}_pre",
            ]

            dependency_arg = self._dependency_arg(class_job_id)
            if dependency_arg is not None:
                sbatch_cmd.append(dependency_arg)

            sbatch_cmd += [
                "--gres=gpu:1",
                "--nodes=1",
                "--time=2-00:00:00",
                "--ntasks=1",
                "--cpus-per-task=1",
                exclude_arg,
                f"--output={slurm_dir.resolve()}/slurm-%j_{case.case_name}_pre.out",
                str(script_path.resolve()),
                str(amber_dir.resolve()),
                str(prmtop.resolve()),
                str(initial_coord.resolve()),
                str(reference_coord.resolve()),
                case.case_name,
                str(pre_mdin.resolve()),
            ]

            result = subprocess.run(
                sbatch_cmd,
                check=True,
                capture_output=True,
                text=True,
                cwd=result_dir.resolve(),
            )

            if result.returncode != 0:
                print("STDOUT:\n", result.stdout)
                print("STDERR:\n", result.stderr)
                raise RuntimeError("sbatch failed")

            pre_job_id = result.stdout.strip().split()[-1]
            ctx.restraint_pre_job_ids[case.case_name] = pre_job_id

            if case.nstlim is None:
                continue

            prod_mdin = input_dir / rendered_restraint_mdin_filename(
                self.OPTIONAL_PRODUCTION_STAGE,
                case.contribution_name,
                case.kappa,
            )
            prod_initial_coord = amber_dir / f"{case.case_name}_pre.restrt"

            if not setup_is_pending:
                self._require_existing_file(prod_mdin, f"restraint production mdin for case {case.case_name}")
            if pre_job_id is None:
                self._require_existing_file(prod_initial_coord, f"restraint pre output coordinate for case {case.case_name}")

            print(f"\033[92m[RESTRAINT_EQ] submit production case {case.case_name}\033[0m")
            prod_cmd = [
                "sbatch",
                f"--job-name={self.cfg.system.name}_{self.cfg.tag}_{case.case_name}_prod",
            ]

            dependency_arg = self._dependency_arg(pre_job_id)
            if dependency_arg is not None:
                prod_cmd.append(dependency_arg)

            prod_cmd += [
                "--gres=gpu:1",
                "--nodes=1",
                "--time=2-00:00:00",
                "--ntasks=1",
                "--cpus-per-task=1",
                exclude_arg,
                f"--output={slurm_dir.resolve()}/slurm-%j_{case.case_name}_prod.out",
                str(script_path.resolve()),
                str(amber_dir.resolve()),
                str(prmtop.resolve()),
                str(prod_initial_coord.resolve()),
                str(reference_coord.resolve()),
                case.case_name,
                str(prod_mdin.resolve()),
            ]

            result = subprocess.run(
                prod_cmd,
                check=True,
                capture_output=True,
                text=True,
                cwd=result_dir.resolve(),
            )

            if result.returncode != 0:
                print("STDOUT:\n", result.stdout)
                print("STDERR:\n", result.stderr)
                raise RuntimeError("sbatch failed")

            ctx.restraint_prod_job_ids[case.case_name] = result.stdout.strip().split()[-1]

    @staticmethod
    def _require_existing_file(path: Path, description: str) -> None:
        if not path.exists():
            raise FileNotFoundError(f"Missing {description}: {path}")

    @classmethod
    def _resolve_class_stage_files(cls, input_dir: Path, target_class: str, require_existing: bool = True) -> list[Path]:
        stage_files = [input_dir / stage_name for stage_name in cls.REQUIRED_EQUILIBRATION_STAGES]
        if require_existing:
            for stage_file in stage_files:
                cls._require_existing_file(stage_file, f"restraint equilibration stage for class {target_class}")
        return stage_files

    @staticmethod
    def _resolve_prmtop(setup_dir: Path, target_class: str) -> Path:
        preferred_path = setup_dir / "prmtop"
        class_specific_path = setup_dir / f"{target_class}.prmtop"
        if preferred_path.exists():
            return preferred_path
        if class_specific_path.exists():
            return class_specific_path
        return preferred_path
