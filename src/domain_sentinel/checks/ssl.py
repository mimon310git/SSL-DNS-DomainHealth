from __future__ import annotations

import math
import socket
import ssl
from datetime import datetime, timezone
from urllib.parse import urlparse

from ..models import CheckResult, Defaults, SiteConfig


def run_ssl_check(site: SiteConfig, defaults: Defaults) -> CheckResult:
    hostname, port = _extract_target(site)
    context = ssl.create_default_context() if defaults.verify_tls else ssl._create_unverified_context()
    if not defaults.verify_tls:
        context.check_hostname = False

    try:
        with socket.create_connection((hostname, port), timeout=defaults.timeout_seconds) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as tls_sock:
                certificate = tls_sock.getpeercert()
                tls_version = tls_sock.version()
                cipher = tls_sock.cipher()[0] if tls_sock.cipher() else None
    except Exception as exc:  # pragma: no cover - network failure path
        return CheckResult(
            name="ssl",
            status="critical",
            summary=f"TLS handshake failed: {exc}",
            details={"host": hostname, "port": port, "error": str(exc)},
        )

    not_after = certificate.get("notAfter")
    expiry = None
    days_to_expiry = None
    if not_after:
        expiry = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
        remaining_seconds = (expiry - datetime.now(timezone.utc)).total_seconds()
        days_to_expiry = math.floor(remaining_seconds / 86400)

    subject = _flatten_name(certificate.get("subject", ()))
    issuer = _flatten_name(certificate.get("issuer", ()))
    san = [value for kind, value in certificate.get("subjectAltName", []) if kind == "DNS"]
    self_signed = bool(subject and issuer and subject == issuer)

    status = "ok"
    issues: list[str] = []
    if days_to_expiry is None:
        status = "critical"
        issues.append("certificate expiry date unavailable")
    else:
        if days_to_expiry <= defaults.ssl_critical_days:
            status = "critical"
            issues.append(f"certificate expires in {days_to_expiry} days")
        elif days_to_expiry <= defaults.ssl_warning_days:
            status = "warning"
            issues.append(f"certificate expires in {days_to_expiry} days")

    if self_signed and status != "critical":
        status = "warning"
        issues.append("certificate appears self-signed")

    if tls_version in {"TLSv1", "TLSv1.1"} and status == "ok":
        status = "warning"
        issues.append(f"legacy TLS version in use: {tls_version}")

    summary = (
        "; ".join(issues)
        if issues
        else f"{tls_version} certificate valid for {days_to_expiry} more days"
    )

    return CheckResult(
        name="ssl",
        status=status,
        summary=summary,
        details={
            "host": hostname,
            "port": port,
            "tls_version": tls_version,
            "cipher": cipher,
            "subject": subject,
            "issuer": issuer,
            "subject_alt_names": san,
            "self_signed": self_signed,
            "expires_at": expiry.isoformat() if expiry else None,
            "days_to_expiry": days_to_expiry,
        },
    )


def _extract_target(site: SiteConfig) -> tuple[str, int]:
    parsed = urlparse(site.url)
    hostname = parsed.hostname or site.domain
    if parsed.port:
        return hostname, parsed.port
    return hostname, 443


def _flatten_name(parts: tuple[tuple[tuple[str, str], ...], ...]) -> str:
    flattened: list[str] = []
    for attributes in parts:
        for key, value in attributes:
            flattened.append(f"{key}={value}")
    return ", ".join(flattened)
