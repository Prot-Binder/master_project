from pathlib import Path


def _create_directories(paths: dict) -> None:
    for value in paths.values():
        if isinstance(value, dict):
            _create_directories(value)
        elif isinstance(value, Path):
            value.mkdir(parents=True, exist_ok=True)