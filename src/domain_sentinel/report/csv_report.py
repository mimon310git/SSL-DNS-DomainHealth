from __future__ import annotations

import csv
from pathlib import Path

from ..models import Snapshot


def write_csv_report(snapshot: Snapshot, path: str | Path) -> None:
    target = Path(path)
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "site_id",
                "domain",
                "url",
                "tags",
                "overall_status",
                "ssl_status",
                "ssl_days_to_expiry",
                "dns_status",
                "http_status",
                "http_status_code",
                "http_response_ms",
                "redirect_status",
                "redirect_final_url",
                "change_count",
            ],
        )
        writer.writeheader()
        for site in snapshot.site_results:
            ssl_check = _find_check(site, "ssl")
            dns_check = _find_check(site, "dns")
            http_check = _find_check(site, "http")
            redirect_check = _find_check(site, "redirect")
            writer.writerow(
                {
                    "site_id": site.id,
                    "domain": site.domain,
                    "url": site.url,
                    "tags": ",".join(site.tags),
                    "overall_status": site.overall_status,
                    "ssl_status": ssl_check.status if ssl_check else "",
                    "ssl_days_to_expiry": (
                        ssl_check.details.get("days_to_expiry") if ssl_check else ""
                    ),
                    "dns_status": dns_check.status if dns_check else "",
                    "http_status": http_check.status if http_check else "",
                    "http_status_code": http_check.details.get("status_code") if http_check else "",
                    "http_response_ms": http_check.details.get("response_ms") if http_check else "",
                    "redirect_status": redirect_check.status if redirect_check else "",
                    "redirect_final_url": (
                        redirect_check.details.get("final_url") if redirect_check else ""
                    ),
                    "change_count": len(site.changes),
                }
            )


def _find_check(site, name: str):
    for check in site.checks:
        if check.name == name:
            return check
    return None
