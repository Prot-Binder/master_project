# src/methods/base.py
from src.config import Config
from src.methods import JobContext


class BaseMethod:
    def __init__(self, cfg):
        self.cfg = cfg

    def prepare(self, run_dir):
        raise NotImplementedError

    def launch(self, cfg: Config, ctx: JobContext) -> str:
        raise NotImplementedError

    def analyze(self, run_dir):
        pass  # optional
