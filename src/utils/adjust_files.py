from __future__ import annotations
from pathlib import Path
from typing import Mapping

def adjust_template_file(template_path: Path, out_path: Path, values: Mapping[str, object]) -> None:
    text = template_path.read_text()
    rendered = text.format(**{k: str(v) for k, v in values.items()})
    out_path.write_text(rendered)
    # out_path.write_text(text)
