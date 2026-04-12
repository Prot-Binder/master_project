from pathlib import Path


def check_eq_exists(eq_outdir: Path) -> bool:
    last_rstfile = eq_outdir / "restrt4"
    return last_rstfile.exists()