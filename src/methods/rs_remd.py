# src/methods/rs_remd.py
from .base_method import BaseMethod
from src.config import Config

# from src.utils.shell import run

class RSREMDMethod(BaseMethod):
    def prepare(self, run_dir):
        # generate replicas, mdin, restraints
        pass

    def launch(self, run_dir, cfg: Config):
        pass
        # if self.cfg.scheduler.type == "slurm":
        #     run(["sbatch", "submit_rs_remd.slurm"], cwd=run_dir)
        # else:
        #     pass
