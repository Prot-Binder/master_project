from src.config import Config
from src.methods.us.us import *
from src.methods.eq.eq import *

def select_method(cfg: Config) -> BaseMethod:
    if cfg.method.name == "eq":
        return None
    if cfg.method.name == "us":
        return USMethod(cfg)
    return None


def create_eq(cfg: Config) -> BaseMethod:
    return EqMethod(cfg)

def create_pull(cfg: Config) -> BaseMethod:
    from src.methods.pull.pull import PullMethod
    return PullMethod(cfg)