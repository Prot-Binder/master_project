from __future__ import annotations

from collections.abc import Iterator

from src.methods.base_method import BaseMethod
from src.methods.method_selector import select_method
from src.methods.restraint_eq.restraint_eq import RestraintEqLauncher
from src.utils.iterate_configured_methods import get_configured_method_names


def iter_launchers(cfg) -> Iterator[BaseMethod]:
    for method_name in get_configured_method_names(cfg):
        yield select_method(method_name, cfg)


def launch_configured_jobs(cfg, ctx) -> None:
    for launcher in iter_launchers(cfg):
        launcher.launch(ctx)

    if cfg.restraints is not None and len(cfg.restraints.contributions) > 0:
        RestraintEqLauncher(cfg).launch(ctx)
