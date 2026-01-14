# src/methods/__init__.py
from .rs_remd import RSREMDMethod
from src.methods.us.us import USMethod

def method_factory(cfg):
    if cfg.method == "rs_remd":
        return RSREMDMethod(cfg)
    if cfg.method == "us":
        return USMethod(cfg)
    raise ValueError(f"Unknown method: {cfg.method}")
