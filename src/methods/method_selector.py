from src.config import Config
from src.methods.pull.pull import PullMethod
from src.methods.rs_remd.rs_remd import RSREMDMethod
from src.methods.us.us import *
from src.methods.eq.eq import *

def select_method(method, cfg) -> BaseMethod:
    if method == "eq":
        return EqMethod(cfg)
    elif method == "pull":
        return PullMethod(cfg)
    if method == "us":
        return USMethod(cfg)
    if method == "rs_remd":
        return RSREMDMethod(cfg)
    raise ValueError(f"Method {method} currently not defined. Implement it yourself!")