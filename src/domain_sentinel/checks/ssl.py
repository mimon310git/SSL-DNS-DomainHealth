from __future__ import annotations

import math
import socket
import ssl
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from ..models import CheckResult, Defaults, SiteConfig


LEGACY_TLS_VERSIONS = {"TLSv1", "TLSv1.1"}


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
    except ssl.SSLCertVerificationError as exc:  # pragma: no cover - network failure path
        mismatch = "hostname" in str(exc).lower() or "match" in str(exc).lower()
        return CheckResult(
            name="ssl",
            status="critical",
            summary=(
                f"TLS handshake failed: hostname mismatch for {hostname}"
                if mismatch
                else f"TLS handshake failed: {exc}"
            ),
            details={
                "host": hostname,
                "port": port,
                "error": str(exc),
                "hostname_mismatch": mismatch,
            },
        )
    except Exception as exc:  # pragma: no cover - network failure path
        return CheckResult(
            name="ssl",
            status="critical",
            summary=f"TLS handshake failed: {exc}",
            details={"host": hostname, "port": port, "error": str(exc)},
        )

    status, issues, details = evaluate_certificate(hostname, port, certificate, tls_version, defaults)
    details["cipher"] = cipher

    summary = (
        "; ".join(issues)
        if issues
        else f"{tls_version} certificate valid for {details['days_to_expiry']} more days"
    )

    return CheckResult(
        name="ssl",
        status=status,
        summary=summary,
        details=details,
    )


def evaluate_certificate(
    hostname: str,
    port: int,
    certificate: dict[str, Any],
    tls_version: str | None,
    defaults: Defaults,
) -> tuple[str, list[str], dict[str, Any]]:
    not_after = certificate.get("notAfter")
    expiry = None
    days_to_expiry = None
    if not_after:
        expiry = datetime.strptime(str(not_after), "%b %d %H:%M:%S %Y %Z").replace(
            tzinfo=timezone.utc
        )
        remaining_seconds = (expiry - datetime.now(timezone.utc)).total_seconds()
        days_to_expiry = math.floor(remaining_seconds / 86400)

    subject = _flatten_name(certificate.get("subject", ()))
    issuer = _flatten_name(certificate.get("issuer", ()))
    san = [value for kind, value in certificate.get("subjectAltName", []) if kind == "DNS"]
    self_signed = bool(subject and issuer and subject == issuer)

    status = "ok"
    issues: list[str] = []
    hostname_mismatch = not _certificate_matches_hostname(certificate, hostname)
    if hostname_mismatch:
        status = "critical"
        issues.append(f"hostname mismatch: certificate does not match {hostname}")

    if days_to_expiry is None:
        status = "critical"
        issues.append("certificate expiry date unavailable")
    else:
        if days_to_expiry <= defaults.ssl_critical_days:
            status = "critical"
            issues.append(f"certificate expires in {days_to_expiry} days")
        elif days_to_expiry <= defaults.ssl_warning_days and status != "critical":
            status = "warning"
            issues.append(f"certificate expires in {days_to_expiry} days")

    if self_signed:
        status = "critical"
        issues.append("certificate is self-signed")

    if tls_version in LEGACY_TLS_VERSIONS:
        status = "critical"
        issues.append(f"legacy TLS version in use: {tls_version}")

    details = {
        "host": hostname,
        "port": port,
        "tls_version": tls_version,
        "subject": subject,
        "issuer": issuer,
        "subject_alt_names": san,
        "self_signed": self_signed,
        "hostname_mismatch": hostname_mismatch,
        "expires_at": expiry.isoformat() if expiry else None,
        "days_to_expiry": days_to_expiry,
    }
    return status, issues, details


def _certificate_matches_hostname(certificate: dict[str, Any], hostname: str) -> bool:
    normalized_host = hostname.rstrip('.').lower()
    san_entries = [value for kind, value in certificate.get("subjectAltName", []) if kind == "DNS"]
    if san_entries:
        return any(_dnsname_matches(pattern, normalized_host) for pattern in san_entries)

    for attributes in certificate.get("subject", ()):
        for key, value in attributes:
            if key == "commonName" and _dnsname_matches(str(value), normalized_host):
                return True
    return False


def _dnsname_matches(pattern: str, hostname: str) -> bool:
    candidate = pattern.rstrip('.').lower()
    if candidate == hostname:
        return True
    if candidate.startswith('*.'):
        suffix = candidate[1:]
        return hostname.endswith(suffix) and hostname.count('.') == candidate.count('.')
    return False


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
