from __future__ import annotations
import subprocess
from pathlib import Path
from typing import Sequence, Optional

def run(cmd: Sequence[str], *, cwd: Optional[Path] = None) -> None:
    # Prints the command for debugging; remove if you prefer quiet
    print("RUN:", " ".join(map(str, cmd)))
    subprocess.run(list(cmd), check=True, cwd=str(cwd) if cwd else None)
