from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.config import Config


def format_restraint_kappa_token(kappa: float) -> str:
    return f"{float(kappa):.2f}"


def build_restraint_case_name(contribution_name: str, kappa: float) -> str:
    return f"{contribution_name}_k{format_restraint_kappa_token(kappa).replace('.', 'p')}"


def rendered_restraint_filename(source_filename: str, kappa: float) -> str:
    path = Path(source_filename)
    return f"{path.stem}{format_restraint_kappa_token(kappa)}{path.suffix}"


def rendered_restraint_mdin_filename(template_filename: str, contribution_name: str, kappa: float) -> str:
    path = Path(template_filename)
    return (
        f"{path.stem}."
        f"{format_restraint_kappa_token(kappa)}."
        f"{build_restraint_case_name(contribution_name, kappa)}"
        f"{path.suffix}"
    )


@dataclass(frozen=True)
class RestraintCase:
    target_class: str
    contribution_name: str
    kappa: float
    nstlim: int | None = None

    @property
    def case_name(self) -> str:
        return build_restraint_case_name(self.contribution_name, self.kappa)


@dataclass(frozen=True)
class RestraintSetupGroup:
    target_class: str
    cases: list[RestraintCase]


def expand_restraint_cases(cfg: Config) -> list[RestraintCase]:
    if cfg.restraints is None:
        return []

    cases: list[RestraintCase] = []
    for contribution in cfg.restraints.contributions:
        for kappa in contribution.kappa:
            cases.append(
                RestraintCase(
                    target_class=contribution.target_class,
                    contribution_name=contribution.name,
                    kappa=kappa,
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
