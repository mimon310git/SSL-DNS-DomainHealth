from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


Status = str


@dataclass(slots=True)
class Defaults:
    timeout_seconds: int = 8
    ssl_warning_days: int = 21
    ssl_critical_days: int = 7
    user_agent: str = "DomainSentinel/0.1"
    follow_redirects_for_http: bool = True
    max_redirect_hops: int = 5
    verify_tls: bool = True


@dataclass(slots=True)
class SiteConfig:
    id: str
    domain: str
    url: str
    redirect_url: str
    checks: list[str]
    expect: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    enabled: bool = True


@dataclass(slots=True)
class AppConfig:
    version: int
    source_path: str
    defaults: Defaults
    sites: list[SiteConfig]


@dataclass(slots=True)
class CheckResult:
    name: str
    status: Status
    summary: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SiteResult:
    id: str
    domain: str
    url: str
    tags: list[str]
    overall_status: Status
    checks: list[CheckResult]
    changes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class RunSummary:
    overall_status: Status
    total_sites: int
    ok_sites: int
    warning_sites: int
    critical_sites: int


@dataclass(slots=True)
class Snapshot:
    generated_at: str
    config_path: str
    summary: RunSummary
    site_results: list[SiteResult]


@dataclass(slots=True)
class RunExecution:
    snapshot: Snapshot
    output_dir: str
    latest_json_path: str
    latest_csv_path: str
    history_json_path: str
    used_previous_snapshot: bool

