from __future__ import annotations

from urllib.parse import urljoin

from ..models import CheckResult, Defaults, SiteConfig
from .http import fetch_url


REDIRECT_CODES = {301, 302, 303, 307, 308}


def run_redirect_check(site: SiteConfig, defaults: Defaults) -> CheckResult:
    current_url = site.redirect_url
    visited = {current_url}
    chain: list[dict[str, object]] = []

    try:
        for _ in range(defaults.max_redirect_hops):
            step = fetch_url(
                current_url,
                defaults.timeout_seconds,
                defaults.user_agent,
                follow_redirects=False,
                verify_tls=defaults.verify_tls,
            )
            location = step["headers"].get("Location") or step["headers"].get("location")
            chain.append(
                {
                    "url": current_url,
                    "status_code": step["status_code"],
                    "location": location,
                    "response_ms": step["response_ms"],
                }
            )
            if int(step["status_code"]) not in REDIRECT_CODES:
                break
            if not location:
                return CheckResult(
                    name="redirect",
                    status="critical",
                    summary="Redirect response missing Location header.",
                    details={"chain": chain},
                )
            next_url = urljoin(current_url, str(location))
            if next_url in visited:
                return CheckResult(
                    name="redirect",
                    status="critical",
                    summary=f"Redirect loop detected at {next_url}",
                    details={"chain": chain, "loop": True},
                )
            visited.add(next_url)
            current_url = next_url
        else:
            return CheckResult(
                name="redirect",
                status="critical",
                summary=f"Redirect chain exceeded {defaults.max_redirect_hops} hops.",
                details={"chain": chain, "too_many_hops": True},
            )
    except Exception as exc:  # pragma: no cover - network failure path
        return CheckResult(
            name="redirect",
            status="critical",
            summary=f"Redirect check failed: {exc}",
            details={"url": site.redirect_url, "error": str(exc)},
        )

    final_url = chain[-1]["url"] if chain else site.redirect_url
    final_status_code = chain[-1]["status_code"] if chain else None
    expect = site.expect
    status = "ok"
    issues: list[str] = []
    expected_final_url = expect.get("final_url")

    if expected_final_url and str(expected_final_url) != str(final_url):
        status = "warning"
        issues.append(f"expected final URL {expected_final_url}, got {final_url}")

    if chain and len(chain) == 1 and int(chain[0]["status_code"]) not in REDIRECT_CODES and expected_final_url:
        if status == "ok":
            status = "warning"
        issues.append("expected redirect chain but request finished without redirect")

    summary = "; ".join(issues) if issues else f"Final URL {final_url} ({final_status_code})"
    return CheckResult(
        name="redirect",
        status=status,
        summary=summary,
        details={
            "start_url": site.redirect_url,
            "final_url": final_url,
            "final_status_code": final_status_code,
            "chain": chain,
        },
    )
