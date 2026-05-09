from pathlib import Path


def create_directories(paths: dict) -> None:
    for value in paths.values():
        if isinstance(value, dict):
            create_directories(value)
        elif isinstance(value, Path):
            value.mkdir(parents=True, exist_ok=True)
