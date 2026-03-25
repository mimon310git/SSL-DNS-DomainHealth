from __future__ import annotations

from typing import Any


def compare_snapshots(previous: dict[str, Any] | None, current: dict[str, Any]) -> dict[str, list[str]]:
    if not previous:
        return {}

    previous_sites = {site["id"]: site for site in previous.get("site_results", [])}
    changes_by_site: dict[str, list[str]] = {}

    for site in current.get("site_results", []):
        site_id = site["id"]
        previous_site = previous_sites.get(site_id)
        changes: list[str] = []
        if previous_site is None:
            changes.append("Site is new since the previous run.")
            changes_by_site[site_id] = changes
            continue

        if previous_site.get("overall_status") != site.get("overall_status"):
            changes.append(
                "Overall status changed from "
                f"{previous_site.get('overall_status')} to {site.get('overall_status')}."
            )

        previous_checks = {item["name"]: item for item in previous_site.get("checks", [])}
        for check in site.get("checks", []):
            before = previous_checks.get(check["name"])
            if before is None:
                changes.append(f"{check['name']} check was added.")
                continue
            if before.get("status") != check.get("status"):
                changes.append(
                    f"{check['name']} status changed from "
                    f"{before.get('status')} to {check.get('status')}."
                )
            changes.extend(_compare_check_details(check["name"], before, check))

        if changes:
            changes_by_site[site_id] = changes

    return changes_by_site


def _compare_check_details(name: str, before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    messages: list[str] = []
    before_details = before.get("details", {})
    after_details = after.get("details", {})

    if name == "ssl":
        if before_details.get("expires_at") != after_details.get("expires_at"):
            messages.append(
                "SSL expiry changed from "
                f"{before_details.get('expires_at')} to {after_details.get('expires_at')}."
            )
        if before_details.get("issuer") != after_details.get("issuer"):
            messages.append(
                "SSL issuer changed from "
                f"{before_details.get('issuer')} to {after_details.get('issuer')}."
            )
        if before_details.get("tls_version") != after_details.get("tls_version"):
            messages.append(
                "TLS version changed from "
                f"{before_details.get('tls_version')} to {after_details.get('tls_version')}."
            )

    if name == "domain_expiration":
        if before_details.get("expires_at") != after_details.get("expires_at"):
            messages.append(
                "Domain expiry changed from "
                f"{before_details.get('expires_at')} to {after_details.get('expires_at')}."
            )
        if before_details.get("registered_domain") != after_details.get("registered_domain"):
            messages.append(
                "Registered domain changed from "
                f"{before_details.get('registered_domain')} to {after_details.get('registered_domain')}."
            )

    if name == "dns":
        before_records = before_details.get("actual_records", {})
        after_records = after_details.get("actual_records", {})
        for record_type in sorted(set(before_records) | set(after_records)):
            if before_records.get(record_type) != after_records.get(record_type):
                messages.append(
                    f"{record_type} records changed from "
                    f"{before_records.get(record_type, [])} to {after_records.get(record_type, [])}."
                )

    if name == "redirect":
        if before_details.get("final_url") != after_details.get("final_url"):
            messages.append(
                "Redirect final URL changed from "
                f"{before_details.get('final_url')} to {after_details.get('final_url')}."
            )
        if before_details.get("final_status_code") != after_details.get("final_status_code"):
            messages.append(
                "Redirect final status changed from "
                f"{before_details.get('final_status_code')} to "
                f"{after_details.get('final_status_code')}."
            )

    if name == "http":
        if before_details.get("status_code") != after_details.get("status_code"):
            messages.append(
                "HTTP status changed from "
                f"{before_details.get('status_code')} to {after_details.get('status_code')}."
            )
        if before_details.get("final_url") != after_details.get("final_url"):
            messages.append(
                "HTTP final URL changed from "
                f"{before_details.get('final_url')} to {after_details.get('final_url')}."
            )

    if name == "security_headers":
        if before_details.get("missing_headers") != after_details.get("missing_headers"):
            messages.append(
                "Missing security headers changed from "
                f"{before_details.get('missing_headers', [])} to {after_details.get('missing_headers', [])}."
            )
        if before_details.get("invalid_headers") != after_details.get("invalid_headers"):
            messages.append(
                "Invalid security headers changed from "
                f"{before_details.get('invalid_headers', [])} to {after_details.get('invalid_headers', [])}."
            )

    return messages