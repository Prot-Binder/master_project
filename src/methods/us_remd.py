# src/methods/us_remd.py
from .base_method import BaseMethod
# from src.utils.shell import run

class USREMDMethod(BaseMethod):
    def prepare(self, run_dir):
        # generate replicas, mdin, restraints
        pass

    def launch(self, run_dir):
        pass
        # if self.cfg.scheduler.type == "slurm":
        #     run(["sbatch", "submit_rs_remd.slurm"], cwd=run_dir)
        # else:
        #     pass
