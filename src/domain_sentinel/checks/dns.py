from __future__ import annotations

import json
import platform
import re
import shutil
import socket
import subprocess

from ..models import CheckResult, Defaults, SiteConfig


def run_dns_check(site: SiteConfig, defaults: Defaults) -> CheckResult:
    expectations = site.expect.get("dns", {})
    record_types = [key for key in expectations.keys() if key != "TXT_CONTAINS"] or ["A"]

    actual_records: dict[str, list[str]] = {}
    issues: list[str] = []
    status = "ok"

    for record_type in record_types:
        try:
            actual = resolve_record(site.domain, record_type, defaults.timeout_seconds)
        except Exception as exc:  # pragma: no cover - network failure path
            actual = []
            if expectations:
                status = "critical"
                issues.append(f"{record_type} lookup failed: {exc}")
        actual_records[record_type] = actual

        if record_type in expectations:
            expected = sorted({str(item).rstrip('.') for item in expectations[record_type]})
            actual_normalized = sorted({item.rstrip('.') for item in actual})
            if expected != actual_normalized:
                if status == "ok":
                    status = "warning"
                issues.append(f"{record_type} mismatch: expected {expected}, got {actual_normalized}")

    if "TXT_CONTAINS" in expectations:
        try:
            txt_records = resolve_record(site.domain, "TXT", defaults.timeout_seconds)
        except Exception as exc:  # pragma: no cover - network failure path
            txt_records = []
            if status == "ok":
                status = "critical"
            issues.append(f"TXT lookup failed: {exc}")
        actual_records["TXT"] = txt_records
        combined_txt = " ".join(txt_records)
        for token in expectations["TXT_CONTAINS"]:
            if str(token) not in combined_txt:
                if status == "ok":
                    status = "warning"
                issues.append(f"TXT record missing token '{token}'")

    if not expectations:
        has_any_record = any(actual_records.values())
        if not has_any_record:
            status = "critical"
            issues.append("domain did not resolve any A record")

    summary = "; ".join(issues) if issues else "DNS records matched expectations"
    return CheckResult(
        name="dns",
        status=status,
        summary=summary,
        details={"domain": site.domain, "actual_records": actual_records},
    )


def resolve_record(domain: str, record_type: str, timeout_seconds: int) -> list[str]:
    normalized_type = record_type.upper()
    if normalized_type == "A":
        return _resolve_ip(domain, socket.AF_INET)
    if normalized_type == "AAAA":
        return _resolve_ip(domain, socket.AF_INET6)

    if platform.system() == "Windows":
        try:
            return _resolve_with_powershell(domain, normalized_type, timeout_seconds)
        except Exception:
            pass

    return _resolve_with_nslookup(domain, normalized_type, timeout_seconds)


def _resolve_ip(domain: str, family: int) -> list[str]:
    records = set()
    for item in socket.getaddrinfo(domain, None, family, socket.SOCK_STREAM):
        address = item[4][0]
        if "%" in address:
            address = address.split("%", 1)[0]
        records.add(address)
    return sorted(records)


def _resolve_with_powershell(domain: str, record_type: str, timeout_seconds: int) -> list[str]:
    command = (
        "$ErrorActionPreference = 'Stop'; "
        f"Resolve-DnsName -Name '{domain}' -Type {record_type} -QuickTimeout "
        "| Select-Object IPAddress,NameHost,NameExchange,Strings "
        "| ConvertTo-Json -Compress"
    )
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-Command", command],
        check=True,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    payload = completed.stdout.strip()
    if not payload:
        return []
    loaded = json.loads(payload)
    if isinstance(loaded, dict):
        loaded = [loaded]

    values: list[str] = []
    for item in loaded:
        if record_type in {"CNAME", "NS"} and item.get("NameHost"):
            values.append(str(item["NameHost"]).rstrip('.'))
        elif record_type == "MX" and item.get("NameExchange"):
            values.append(str(item["NameExchange"]).rstrip('.'))
        elif record_type == "TXT" and item.get("Strings"):
            strings = item["Strings"]
            if isinstance(strings, list):
                values.append("".join(str(part) for part in strings))
            else:
                values.append(str(strings))
        elif item.get("IPAddress"):
            values.append(str(item["IPAddress"]))
    return sorted(set(values))


def _resolve_with_nslookup(domain: str, record_type: str, timeout_seconds: int) -> list[str]:
    executable = shutil.which("nslookup")
    if not executable:
        raise RuntimeError("No supported DNS resolver found. Install nslookup or run on Windows.")

    completed = subprocess.run(
        [executable, f"-type={record_type}", domain],
        check=True,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    return _parse_nslookup_output(completed.stdout, record_type)


def _parse_nslookup_output(output: str, record_type: str) -> list[str]:
    values: set[str] = set()
    if record_type == "NS":
        matches = re.findall(r"nameserver\s*=\s*(.+)", output, flags=re.IGNORECASE)
        values.update(match.strip().rstrip('.') for match in matches)
    elif record_type == "CNAME":
        matches = re.findall(r"canonical name\s*=\s*(.+)", output, flags=re.IGNORECASE)
        values.update(match.strip().rstrip('.') for match in matches)
    elif record_type == "MX":
        matches = re.findall(r"mail exchanger\s*=\s*\d+\s+(.+)", output, flags=re.IGNORECASE)
        values.update(match.strip().rstrip('.') for match in matches)
    elif record_type == "TXT":
        matches = re.findall(r"text\s*=\s*\"(.+?)\"", output, flags=re.IGNORECASE)
        values.update(match.strip() for match in matches)
    return sorted(values)
