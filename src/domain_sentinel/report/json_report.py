from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_json_report(payload: dict[str, Any], path: str | Path) -> None:
    target = Path(path)
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
