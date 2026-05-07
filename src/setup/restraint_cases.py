from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.config import Config


@dataclass(frozen=True)
class RestraintCase:
    target_class: str
    contribution_name: str
    index: int
    kappa: float
    nstlim: int | None = None

    @property
    def case_name(self) -> str:
        kappa_token = f"{self.kappa:.4f}".rstrip("0").rstrip(".").replace(".", "p")
        return f"{self.contribution_name}_idx{self.index}_k{kappa_token}"


@dataclass(frozen=True)
class RestraintSetupGroup:
    target_class: str
    cases: list[RestraintCase]


def expand_restraint_cases(cfg: Config) -> list[RestraintCase]:
    if cfg.restraints is None:
        return []

    cases: list[RestraintCase] = []
    for contribution in cfg.restraints.contributions:
        for point in contribution.points:
            cases.append(
                RestraintCase(
                    target_class=contribution.target_class,
                    contribution_name=contribution.name,
                    index=point.index,
                    kappa=point.kappa,
                    nstlim=contribution.nstlim,
                )
            )
    return cases


def group_restraint_cases_by_class(cfg: Config) -> list[RestraintSetupGroup]:
    grouped_cases: dict[str, list[RestraintCase]] = {
        "complex": [],
        "receptor": [],
        "ligand": [],
    }

    for case in expand_restraint_cases(cfg):
        grouped_cases[case.target_class].append(case)

    groups: list[RestraintSetupGroup] = []
    for target_class in ("complex", "receptor", "ligand"):
        cases = grouped_cases[target_class]
        if len(cases) == 0:
            continue
        groups.append(
            RestraintSetupGroup(
                target_class=target_class,
                cases=cases,
            )
        )

    return groups
