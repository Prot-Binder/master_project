from pathlib import Path


def check_eq_exists(eq_indir: Path) -> bool:
    # last_rstfile = eq_outdir / "restrt4"
    last_rstfile = eq_indir / "inpcrd4"
    return last_rstfile.exists()