from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from ..models import Snapshot
from ..report.csv_report import write_csv_report
from ..report.html_report import write_html_report
from ..report.json_report import write_json_report


def load_latest_snapshot(output_dir: str | Path) -> dict[str, Any] | None:
    latest_path = Path(output_dir) / "latest.json"
    if not latest_path.exists():
        return None
    return json.loads(latest_path.read_text(encoding="utf-8"))


def save_snapshot_bundle(output_dir: str | Path, snapshot: Snapshot) -> dict[str, str]:
    root = Path(output_dir)
    runs_dir = root / "runs"
    root.mkdir(parents=True, exist_ok=True)
    runs_dir.mkdir(parents=True, exist_ok=True)

    snapshot_dict = asdict(snapshot)
    timestamp = snapshot.generated_at.replace(":", "").replace("-", "").replace("+00:00", "Z")
    history_json_path = runs_dir / f"{timestamp}.json"
    latest_json_path = root / "latest.json"
    latest_csv_path = root / "latest.csv"
    latest_html_path = root / "latest.html"

    write_json_report(snapshot_dict, history_json_path)
    write_json_report(snapshot_dict, latest_json_path)
    write_csv_report(snapshot, latest_csv_path)
    write_html_report(snapshot, latest_html_path)

    return {
        "history_json_path": str(history_json_path),
        "latest_json_path": str(latest_json_path),
        "latest_csv_path": str(latest_csv_path),
        "latest_html_path": str(latest_html_path),
    }
