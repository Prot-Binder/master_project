from __future__ import annotations

from dataclasses import dataclass, field

@dataclass
class JobContext:
    paths: dict = field(default_factory=dict)
    cfg_path: str | None = None
    setup_job_id: str | None = None
    eq_job_id: str | None = None
    restraint_eq_job_ids: dict[str, str] | None = None
    pull_job_ids: dict[float, str] | None = None
    us_job_ids: dict[float, str] | None = None
    us_remd_job_ids: dict[int, str] | None = None
    rsremd_eq_job_id: str | None = None
    rsremd_setup_job_id: str | None = None
    rsremd_eq_each_job_id: str | None = None
    rsremd_prod_job_id: str | None = None
    com_distance: float | None = None
    restraint_setup_artifacts: dict[str, dict[str, str]] | None = None
