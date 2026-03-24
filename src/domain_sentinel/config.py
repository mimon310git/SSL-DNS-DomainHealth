from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .models import AppConfig, Defaults, SiteConfig


DEFAULT_CHECKS = ["ssl", "dns", "redirect", "http"]
SUPPORTED_CHECKS = set(DEFAULT_CHECKS)


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path).expanduser().resolve()
    raw = _read_config_file(config_path)
    version = int(raw.get("version", 1))
    defaults = _build_defaults(raw.get("defaults", {}))
    sites_data = raw.get("sites")
    if not isinstance(sites_data, list) or not sites_data:
        raise ValueError("Config must define a non-empty 'sites' list.")

    seen_ids: set[str] = set()
    sites: list[SiteConfig] = []
    for item in sites_data:
        if not isinstance(item, dict):
            raise ValueError("Every site entry must be an object.")
        site = _build_site(item)
        if site.id in seen_ids:
            raise ValueError(f"Duplicate site id '{site.id}' in config.")
        seen_ids.add(site.id)
        sites.append(site)

    return AppConfig(
        version=version,
        source_path=str(config_path),
        defaults=defaults,
        sites=sites,
    )


def _read_config_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    suffix = path.suffix.lower()
    if suffix == ".json":
        return json.loads(path.read_text(encoding="utf-8-sig"))
    if suffix in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore
        except ModuleNotFoundError as exc:
            raise ValueError(
                "YAML config requires PyYAML. Install it with "
                "'python -m pip install PyYAML' or use JSON instead."
            ) from exc
        loaded = yaml.safe_load(path.read_text(encoding="utf-8-sig"))
        if not isinstance(loaded, dict):
            raise ValueError("YAML config root must be an object.")
        return loaded
    raise ValueError("Unsupported config format. Use .json, .yaml, or .yml.")


def _build_defaults(raw: dict[str, Any]) -> Defaults:
    if not isinstance(raw, dict):
        raise ValueError("'defaults' must be an object if provided.")

    defaults = Defaults(
        timeout_seconds=int(raw.get("timeout_seconds", 8)),
        ssl_warning_days=int(raw.get("ssl_warning_days", 21)),
        ssl_critical_days=int(raw.get("ssl_critical_days", 7)),
        user_agent=str(raw.get("user_agent", "DomainSentinel/0.1")),
        follow_redirects_for_http=bool(raw.get("follow_redirects_for_http", True)),
        max_redirect_hops=int(raw.get("max_redirect_hops", 5)),
        verify_tls=bool(raw.get("verify_tls", True)),
    )
    if defaults.timeout_seconds <= 0:
        raise ValueError("'timeout_seconds' must be greater than zero.")
    if defaults.ssl_critical_days < 0 or defaults.ssl_warning_days < 0:
        raise ValueError("SSL thresholds must be zero or greater.")
    if defaults.ssl_critical_days > defaults.ssl_warning_days:
        raise ValueError("'ssl_critical_days' cannot be greater than 'ssl_warning_days'.")
    if defaults.max_redirect_hops <= 0:
        raise ValueError("'max_redirect_hops' must be greater than zero.")
    return defaults


def _build_site(raw: dict[str, Any]) -> SiteConfig:
    expect = _normalize_expectations(raw)
    provided_url = raw.get("url")
    provided_domain = raw.get("domain")

    if provided_domain:
        domain = str(provided_domain).strip()
    elif provided_url:
        parsed = urlparse(str(provided_url))
        if not parsed.hostname:
            raise ValueError("Site url must include a hostname.")
        domain = parsed.hostname
    else:
        raise ValueError("Each site must include either 'domain' or 'url'.")

    if not domain:
        raise ValueError("Site domain cannot be empty.")

    site_id = str(raw.get("id") or domain).strip()
    checks = _normalize_checks(raw.get("checks"))
    url = str(provided_url or f"https://{domain}/").strip()
    redirect_url = str(raw.get("redirect_url") or f"http://{domain}/").strip()

    return SiteConfig(
        id=site_id,
        domain=domain,
        url=url,
        redirect_url=redirect_url,
        checks=checks,
        expect=expect,
        tags=[str(tag) for tag in raw.get("tags", [])],
        enabled=bool(raw.get("enabled", True)),
    )


def _normalize_expectations(raw: dict[str, Any]) -> dict[str, Any]:
    expect = dict(raw.get("expect", {}))
    if "expected_status" in raw and "status_code" not in expect:
        expect["status_code"] = raw["expected_status"]
    if "expected_contains" in raw and "body_contains" not in expect:
        expect["body_contains"] = raw["expected_contains"]
    if "expected_not_contains" in raw and "body_not_contains" not in expect:
        expect["body_not_contains"] = raw["expected_not_contains"]
    if "expected_redirect_to" in raw and "final_url" not in expect:
        expect["final_url"] = raw["expected_redirect_to"]
    if "dns" in raw:
        expect_dns = dict(expect.get("dns", {}))
        expect_dns.update(raw["dns"])
        expect["dns"] = expect_dns

    dns_expect = expect.get("dns")
    if isinstance(dns_expect, dict):
        expect["dns"] = {_normalize_dns_key(key): value for key, value in dns_expect.items()}
    return expect


def _normalize_checks(raw_checks: Any) -> list[str]:
    if raw_checks is None:
        return list(DEFAULT_CHECKS)
    if isinstance(raw_checks, str):
        checks = [raw_checks]
    elif isinstance(raw_checks, list):
        checks = [str(item) for item in raw_checks]
    else:
        raise ValueError("'checks' must be a list of check names.")

    normalized = []
    for check in checks:
        lowered = check.strip().lower()
        if lowered not in SUPPORTED_CHECKS:
            raise ValueError(f"Unsupported check '{check}'.")
        normalized.append(lowered)
    return normalized


def _normalize_dns_key(value: str) -> str:
    lowered = str(value).strip().lower()
    if lowered == "txt_contains":
        return "TXT_CONTAINS"
    return lowered.upper()

