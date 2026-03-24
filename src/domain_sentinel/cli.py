from __future__ import annotations

import argparse
import json
import sys

from .config import load_config
from .models import Snapshot
from .runner import execute_run
from .severity import exit_code_for_status


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="domain-sentinel",
        description="Multi-site SSL, DNS, redirect, and endpoint health manager.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run all checks.")
    run_parser.add_argument("-c", "--config", required=True, help="Path to JSON or YAML config.")
    run_parser.add_argument(
        "-o",
        "--output-dir",
        default="artifacts",
        help="Directory where JSON/CSV reports and snapshots will be written.",
    )
    run_parser.add_argument(
        "--pretty-summary",
        action="store_true",
        help="Print the run summary as JSON after the console report.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        try:
            config = load_config(args.config)
            execution = execute_run(config, args.output_dir)
        except Exception as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 3

        print_console_report(execution.snapshot, execution.latest_json_path, execution.latest_csv_path)
        if args.pretty_summary:
            print(json.dumps(_summary_payload(execution.snapshot), indent=2))
        return exit_code_for_status(execution.snapshot.summary.overall_status)

    parser.print_help()
    return 0


def print_console_report(snapshot: Snapshot, latest_json_path: str, latest_csv_path: str) -> None:
    print(
        f"Domain Sentinel run at {snapshot.generated_at} "
        f"[overall={snapshot.summary.overall_status.upper()}]"
    )
    print(
        f"Sites: {snapshot.summary.total_sites} | OK: {snapshot.summary.ok_sites} | "
        f"Warning: {snapshot.summary.warning_sites} | Critical: {snapshot.summary.critical_sites}"
    )
    print(f"Reports: JSON={latest_json_path} CSV={latest_csv_path}")
    for site in snapshot.site_results:
        print(f"\n[{site.overall_status.upper():8}] {site.id} ({site.domain})")
        for check in site.checks:
            print(f"  - {check.name:<8} {check.status:<8} {check.summary}")
        for change in site.changes:
            print(f"  * change: {change}")


def _summary_payload(snapshot: Snapshot) -> dict[str, object]:
    return {
        "generated_at": snapshot.generated_at,
        "summary": {
            "overall_status": snapshot.summary.overall_status,
            "total_sites": snapshot.summary.total_sites,
            "ok_sites": snapshot.summary.ok_sites,
            "warning_sites": snapshot.summary.warning_sites,
            "critical_sites": snapshot.summary.critical_sites,
        },
    }
