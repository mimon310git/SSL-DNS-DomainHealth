from __future__ import annotations

import json
import math
import urllib.error
import urllib.request
from datetime import datetime, timezone
from urllib.parse import quote

from ..models import CheckResult, Defaults, SiteConfig


RDAP_URL_TEMPLATE = "https://rdap.org/domain/{domain}"


def run_domain_expiration_check(site: SiteConfig, defaults: Defaults) -> CheckResult:
    registered_domain = site.registered_domain or site.domain
    try:
        payload = fetch_rdap_document(
            registered_domain,
            defaults.timeout_seconds,
            defaults.user_agent,
        )
    except Exception as exc:  # pragma: no cover - network failure path
        return CheckResult(
            name="domain_expiration",
            status="warning",
            summary=f"Domain expiry lookup failed: {exc}",
            details={"registered_domain": registered_domain, "error": str(exc)},
        )

    expires_at = extract_expiration_date(payload)
    if expires_at is None:
        return CheckResult(
            name="domain_expiration",
            status="warning",
            summary="RDAP response did not include an expiration date.",
            details={"registered_domain": registered_domain},
        )

    now = datetime.now(timezone.utc)
    remaining_seconds = (expires_at - now).total_seconds()
    days_to_expiry = max(0, math.ceil(remaining_seconds / 86400))
    critical_days = int(site.expect.get("domain_critical_days", defaults.domain_critical_days))
    warning_days = int(site.expect.get("domain_warning_days", defaults.domain_warning_days))

    status = "ok"
    summary = f"Domain registration valid for {days_to_expiry} more days"
    if days_to_expiry <= critical_days:
        status = "critical"
        summary = f"Domain registration expires in {days_to_expiry} days"
    elif days_to_expiry <= warning_days:
        status = "warning"
        summary = f"Domain registration expires in {days_to_expiry} days"

    return CheckResult(
        name="domain_expiration",
        status=status,
        summary=summary,
        details={
            "registered_domain": registered_domain,
            "expires_at": expires_at.replace(microsecond=0).isoformat(),
            "days_to_expiry": days_to_expiry,
        },
    )


def fetch_rdap_document(domain: str, timeout_seconds: int, user_agent: str) -> dict[str, object]:
    url = RDAP_URL_TEMPLATE.format(domain=quote(domain))
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept": "application/rdap+json, application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"RDAP HTTP {exc.code}") from exc


def extract_expiration_date(payload: dict[str, object]) -> datetime | None:
    events = payload.get("events")
    if not isinstance(events, list):
        return None

    candidates: list[datetime] = []
    for event in events:
        if not isinstance(event, dict):
            continue
        action = str(event.get("eventAction", "")).strip().lower()
        if "expir" not in action and "expiry" not in action:
            continue
        event_date = parse_rdap_timestamp(event.get("eventDate"))
        if event_date is not None:
            candidates.append(event_date)

    if not candidates:
        return None
    return max(candidates)


def parse_rdap_timestamp(raw: object) -> datetime | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    normalized = raw.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)