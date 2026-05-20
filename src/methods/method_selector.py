from src.config import Config
from src.methods.gauss_rank.gauss_rank import GaussRankMethod
from src.methods.pull.pull import PullMethod
from src.methods.rs_remd.rs_remd import RSREMDMethod
from src.methods.us_remd.us_remd import USREMDMethod
from src.methods.us.us import *
from src.methods.eq.eq import *

def select_method(method, cfg) -> BaseMethod:
    if method == "eq":
        return EqMethod(cfg)
    elif method == "gauss_rank":
        return GaussRankMethod(cfg)
    elif method == "pull":
        return PullMethod(cfg)
    if method == "us":
        return USMethod(cfg)
    if method == "us_remd":
        return USREMDMethod(cfg)
    if method == "rs_remd":
        return RSREMDMethod(cfg)
    raise ValueError(f"Method {method} currently not defined. Implement it yourself!")
