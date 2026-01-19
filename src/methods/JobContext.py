from __future__ import annotations

from dataclasses import dataclass, field

@dataclass
class JobContext:
    paths: dict = field(default_factory=dict)
    eq_job_id: str | None = None
    job_ids: dict[str, list[str]] = field(default_factory=dict)
