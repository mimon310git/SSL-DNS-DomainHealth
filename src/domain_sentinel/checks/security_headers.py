from __future__ import annotations

from urllib.parse import urlparse

from ..models import CheckResult, Defaults, SiteConfig
from .http import fetch_url


DEFAULT_REQUIRED_HEADERS = [
    "Strict-Transport-Security",
    "X-Content-Type-Options",
    "Content-Security-Policy",
    "X-Frame-Options",
]


def run_security_headers_check(site: SiteConfig, defaults: Defaults) -> CheckResult:
    try:
        result = fetch_url(
            site.url,
            defaults.timeout_seconds,
            defaults.user_agent,
            follow_redirects=True,
            verify_tls=defaults.verify_tls,
        )
    except Exception as exc:  # pragma: no cover - network failure path
        return CheckResult(
            name="security_headers",
            status="critical",
            summary=f"Security header check failed: {exc}",
            details={"url": site.url, "error": str(exc)},
        )

    expect_headers = site.expect.get("security_headers", {})
    required_headers = _normalize_required_headers(expect_headers)
    header_map = {key.lower(): value for key, value in result["headers"].items()}
    final_scheme = urlparse(str(result["final_url"])).scheme.lower()

    status = "ok"
    issues: list[str] = []
    missing_headers: list[str] = []
    invalid_headers: list[str] = []
    found_headers: dict[str, str] = {}

    for header_name in required_headers:
        if header_name == "Strict-Transport-Security" and final_scheme != "https":
            continue
        raw_value = header_map.get(header_name.lower())
        if raw_value is None:
            status = "warning"
            missing_headers.append(header_name)
            continue

        header_value = str(raw_value).strip()
        found_headers[header_name] = header_value
        validation_issue = _validate_header(header_name, header_value)
        if validation_issue:
            status = "warning"
            invalid_headers.append(f"{header_name} ({validation_issue})")

    if int(result["status_code"]) >= 400:
        if status == "ok":
            status = "warning"
        issues.append(f"received HTTP {result['status_code']} while checking headers")
    if missing_headers:
        issues.append(f"missing {', '.join(missing_headers)}")
    if invalid_headers:
        issues.append(f"invalid {', '.join(invalid_headers)}")

    summary = "; ".join(issues) if issues else "Security headers matched policy"
    return CheckResult(
        name="security_headers",
        status=status,
        summary=summary,
        details={
            "url": site.url,
            "final_url": result["final_url"],
            "status_code": result["status_code"],
            "required_headers": required_headers,
            "found_headers": found_headers,
            "missing_headers": missing_headers,
            "invalid_headers": invalid_headers,
        },
    )


def _normalize_required_headers(raw: object) -> list[str]:
    if isinstance(raw, dict):
        required = raw.get("required", DEFAULT_REQUIRED_HEADERS)
    else:
        required = raw or DEFAULT_REQUIRED_HEADERS

    if not isinstance(required, list):
        return list(DEFAULT_REQUIRED_HEADERS)
    return [str(item) for item in required if str(item).strip()]


def _validate_header(name: str, value: str) -> str | None:
    normalized_value = value.lower()
    if name == "Strict-Transport-Security" and "max-age=" not in normalized_value:
        return "expected max-age directive"
    if name == "X-Content-Type-Options" and normalized_value != "nosniff":
        return "expected nosniff"
    if name == "Content-Security-Policy" and not value.strip():
        return "empty value"
    if name == "X-Frame-Options" and normalized_value not in {"deny", "sameorigin"}:
        return "expected DENY or SAMEORIGIN"
    return None