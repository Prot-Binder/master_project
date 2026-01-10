# src/methods/base.py
class BaseMethod:
    def __init__(self, cfg):
        self.cfg = cfg

    def prepare(self, run_dir):
        raise NotImplementedError

    def launch(self, run_dir):
        raise NotImplementedError

    def analyze(self, run_dir):
        pass  # optional
