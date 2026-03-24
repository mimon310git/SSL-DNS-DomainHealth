from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone

from .checks import run_dns_check, run_http_check, run_redirect_check, run_ssl_check
from .diff import compare_snapshots
from .models import AppConfig, CheckResult, RunExecution, RunSummary, SiteResult, Snapshot
from .severity import combine_statuses
from .storage import load_latest_snapshot, save_snapshot_bundle


CHECK_HANDLERS = {
    "ssl": run_ssl_check,
    "dns": run_dns_check,
    "redirect": run_redirect_check,
    "http": run_http_check,
}


def execute_run(config: AppConfig, output_dir: str) -> RunExecution:
    previous_snapshot = load_latest_snapshot(output_dir)
    site_results = [run_site(site, config) for site in config.sites if site.enabled]
    summary = build_summary(site_results)
    snapshot = Snapshot(
        generated_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        config_path=config.source_path,
        summary=summary,
        site_results=site_results,
    )

    changes = compare_snapshots(previous_snapshot, asdict(snapshot))
    for site in snapshot.site_results:
        site.changes = changes.get(site.id, [])

    paths = save_snapshot_bundle(output_dir, snapshot)
    return RunExecution(
        snapshot=snapshot,
        output_dir=output_dir,
        latest_json_path=paths["latest_json_path"],
        latest_csv_path=paths["latest_csv_path"],
        latest_html_path=paths["latest_html_path"],
        history_json_path=paths["history_json_path"],
        used_previous_snapshot=previous_snapshot is not None,
    )


def run_site(site, config: AppConfig) -> SiteResult:
    results: list[CheckResult] = []
    for check_name in site.checks:
        handler = CHECK_HANDLERS[check_name]
        results.append(handler(site, config.defaults))
    overall = combine_statuses(result.status for result in results)
    return SiteResult(
        id=site.id,
        domain=site.domain,
        url=site.url,
        tags=site.tags,
        overall_status=overall,
        checks=results,
    )


def build_summary(site_results: list[SiteResult]) -> RunSummary:
    ok_sites = sum(1 for site in site_results if site.overall_status == "ok")
    warning_sites = sum(1 for site in site_results if site.overall_status == "warning")
    critical_sites = sum(1 for site in site_results if site.overall_status == "critical")
    overall = combine_statuses(site.overall_status for site in site_results)
    return RunSummary(
        overall_status=overall,
        total_sites=len(site_results),
        ok_sites=ok_sites,
        warning_sites=warning_sites,
        critical_sites=critical_sites,
    )
