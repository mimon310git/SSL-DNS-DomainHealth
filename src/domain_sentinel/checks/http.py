from __future__ import annotations

import ssl
import time
import urllib.error
import urllib.request
from typing import Any

from ..models import CheckResult, Defaults, SiteConfig


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[override]
        return None


def _build_opener(*, follow_redirects: bool, context: ssl.SSLContext) -> urllib.request.OpenerDirector:
    handlers: list[urllib.request.BaseHandler] = [urllib.request.HTTPSHandler(context=context)]
    if not follow_redirects:
        handlers.append(_NoRedirectHandler())
    return urllib.request.build_opener(*handlers)


def fetch_url(
    url: str,
    timeout_seconds: int,
    user_agent: str,
    *,
    follow_redirects: bool,
    verify_tls: bool,
) -> dict[str, Any]:
    context = ssl.create_default_context() if verify_tls else ssl._create_unverified_context()
    opener = _build_opener(follow_redirects=follow_redirects, context=context)
    request = urllib.request.Request(url, headers={"User-Agent": user_agent})
    start = time.perf_counter()

    try:
        with opener.open(request, timeout=timeout_seconds) as response:
            body = response.read(1_000_000)
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            return {
                "ok": True,
                "status_code": response.status,
                "final_url": response.geturl(),
                "headers": dict(response.headers.items()),
                "body_text": body.decode("utf-8", errors="replace"),
                "response_ms": elapsed_ms,
            }
    except urllib.error.HTTPError as exc:
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        body = exc.read(1_000_000)
        return {
            "ok": False,
            "status_code": exc.code,
            "final_url": exc.geturl(),
            "headers": dict(exc.headers.items()),
            "body_text": body.decode("utf-8", errors="replace"),
            "response_ms": elapsed_ms,
            "error": str(exc),
        }


def run_http_check(site: SiteConfig, defaults: Defaults) -> CheckResult:
    try:
        result = fetch_url(
            site.url,
            defaults.timeout_seconds,
            defaults.user_agent,
            follow_redirects=defaults.follow_redirects_for_http,
            verify_tls=defaults.verify_tls,
        )
    except Exception as exc:  # pragma: no cover - network failure path
        return CheckResult(
            name="http",
            status="critical",
            summary=f"Request failed: {exc}",
            details={"url": site.url, "error": str(exc)},
        )

    expect = site.expect
    status = "ok"
    issues: list[str] = []

    expected_code = expect.get("status_code")
    if expected_code is not None and int(expected_code) != int(result["status_code"]):
        status = "critical"
        issues.append(f"expected status {expected_code}, got {result['status_code']}")
    elif expected_code is None and int(result["status_code"]) >= 400:
        status = "critical"
        issues.append(f"unexpected status {result['status_code']}")

    expected_text = expect.get("body_contains")
    if expected_text and str(expected_text) not in result["body_text"]:
        status = "critical"
        issues.append(f"response body missing '{expected_text}'")

    forbidden_text = expect.get("body_not_contains")
    if forbidden_text and str(forbidden_text) in result["body_text"]:
        status = "critical"
        issues.append(f"response body unexpectedly contains '{forbidden_text}'")

    max_response_ms = expect.get("max_response_ms")
    if max_response_ms is not None and float(result["response_ms"]) > float(max_response_ms):
        if status == "ok":
            status = "warning"
        issues.append(
            f"response time {result['response_ms']}ms exceeded {float(max_response_ms):.0f}ms"
        )

    summary = (
        "; ".join(issues)
        if issues
        else f"HTTP {result['status_code']} in {result['response_ms']}ms"
    )
    return CheckResult(
        name="http",
        status=status,
        summary=summary,
        details=result,
    )
