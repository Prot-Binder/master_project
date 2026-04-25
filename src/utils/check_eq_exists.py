from pathlib import Path


def check_eq_exists(eq_indir: Path) -> bool:
    last_rstfile = eq_indir / "inpcrd_eq"
    return last_rstfile.exists()
