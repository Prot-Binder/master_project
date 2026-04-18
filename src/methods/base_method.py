# src/methods/base.py
from collections.abc import Iterable

from src.methods import JobContext


class BaseMethod:
    def __init__(self, cfg):
        self.cfg = cfg

    def launch(self, ctx: JobContext) -> str:
        raise NotImplementedError

    def _dependency_arg(self, *job_ids: str | None | Iterable[str | None]) -> str | None:
        dependency_ids: list[str] = []

        for job_id in job_ids:
            if job_id is None:
                continue

            if isinstance(job_id, str):
                values = [job_id]
            else:
                values = job_id

            for value in values:
                if value is None:
                    continue
                value_str = str(value)
                if value_str not in dependency_ids:
                    dependency_ids.append(value_str)

        if not dependency_ids:
            return None

        return f"--dependency=afterok:{':'.join(dependency_ids)}"
