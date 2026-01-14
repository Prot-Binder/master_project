# src/methods/us.py
from src.methods.base_method import BaseMethod
# from src.utils.shell import run

class USMethod(BaseMethod):
    def prepare(self, run_dir):
        # generate replicas, mdin, restraints
        pass

    def launch(self, run_dir):
        run_dir = base_dir / "run_output"
        input_dir = base_dir / "input"
        setup_dir = base_dir / "setup"

        job_id : str = "abc"
        replica: str = "01"
        min: float = 0.0
        max: float = 10.0
        step: float = 0.5

        top_dir: str = "/path/to/top_dir"
        result_dir: str = "/path/to/result_dir"



        run_dir.mkdir(parents=True, exist_ok=True)

        subprocess.run([
            "sbatch",
            f"--chdir={run_dir}",
            "run_us.sh",
            str(window),
            str(input_dir),
            str(setup_dir),
        ])

        pass
        # if self.cfg.scheduler.type == "slurm":
        #     run(["sbatch", "submit_rs_remd.slurm"], cwd=run_dir)
        # else:
        #     pass
