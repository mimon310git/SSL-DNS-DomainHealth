# Domain Sentinel

Domain Sentinel is a small multi-site SSL, DNS, redirect, and endpoint health manager built as a portfolio-ready ops utility.

## What it does

- checks SSL certificate expiry and basic TLS details
- flags hostname mismatch, self-signed certificates, and legacy TLS versions
- checks DNS records against expected values or basic resolvability
- checks redirect behavior and loop risk
- checks HTTP endpoint status, content, and latency threshold
- stores a snapshot from each run
- compares the latest run against the previous run
- exports JSON, CSV, and HTML reports

## Why It Matters

A domain is not just a single web page. A healthy public-facing service depends on multiple layers working together:

- DNS has to resolve to the correct target
- TLS/SSL has to be valid and trustworthy
- redirects have to lead to the correct destination
- the HTTP endpoint has to respond with the expected result

Domain Sentinel treats those layers as one health surface instead of checking only uptime.

## How It Works

### SSL / TLS

The SSL check validates the security layer of the service. It inspects certificate validity, days until expiry, the negotiated TLS version, hostname matching, and basic certificate trust signals such as self-signed detection. This matters because a website can still be online while being close to certificate expiration or using a weak or mismatched TLS setup.

### DNS

The DNS check validates the routing layer of the domain. It confirms that the domain resolves and, when expectations are configured, that the resolved records match the intended state. This matters because a service may fail even when the application itself is healthy if DNS points to the wrong place.

### Redirects

The redirect check validates URL flow correctness. It follows the redirect chain, detects loops, and reports the final destination. This matters because many production sites rely on predictable redirects such as `http -> https` or `apex -> www`.

### HTTP

The HTTP check validates application-level availability. It checks whether an endpoint responds, returns the expected status code, contains expected content, and stays within an acceptable latency threshold. This is the closest layer to what a real user or client actually experiences.

### Snapshot Diffing

A one-time check only describes the current state. Domain Sentinel also stores snapshots and compares the current run with the previous one. This turns the tool from a simple checker into a small monitoring utility that can answer not only \"what is wrong now\" but also \"what changed since the last run\".

### JSON / CSV Reporting

The reporting layer makes the results reusable. JSON is intended for automation and downstream processing, while CSV is intended for quick inspection and lightweight reporting. That makes the project useful both for terminal use and for future integrations.

### HTML Reporting

The HTML report turns the latest run into a shareable visual summary. Instead of reading raw JSON or terminal output, a user can open a single file and inspect overall status, per-site results, and detected changes in a more presentation-friendly format.

## Stack

- Python 3.12
- standard library only for the MVP
- optional YAML support when `PyYAML` is installed

## Quick Start

Run from the repository root:

```powershell
python main.py run -c configs/domains.example.json --pretty-summary
```

On Windows, `py` works too:

```powershell
py main.py run -c configs/domains.example.json --pretty-summary
```

If you want an installed CLI command:

```powershell
python -m pip install -e .
domain-sentinel run -c configs/domains.example.json --pretty-summary
```

If you want YAML config support later:

```powershell
python -m pip install PyYAML
```

Then:

```powershell
python main.py run -c configs/domains.example.yaml
```

Open the generated HTML report:

```powershell
start artifacts\latest.html
```

## Config Example

JSON works out of the box:

```json
{
  "version": 1,
  "defaults": {
    "timeout_seconds": 8,
    "ssl_warning_days": 21,
    "ssl_critical_days": 7,
    "max_redirect_hops": 5
  },
  "sites": [
    {
      "id": "company-main",
      "domain": "example.com",
      "url": "https://example.com/",
      "checks": ["ssl", "dns", "redirect", "http"],
      "expect": {
        "status_code": 200,
        "body_contains": "Example Domain"
      }
    }
  ]
}
```

Supported expectations:

- `status_code`
- `body_contains`
- `body_not_contains`
- `max_response_ms`
- `final_url`
- `dns.A`, `dns.AAAA`, `dns.CNAME`, `dns.MX`, `dns.NS`, `dns.TXT`
- `dns.TXT_CONTAINS`

## Output

Each run writes:

- `artifacts/latest.json`
- `artifacts/latest.csv`
- `artifacts/latest.html`
- `artifacts/runs/<timestamp>.json`

Exit codes:

- `0` = all OK
- `1` = warnings found
- `2` = critical issues found
- `3` = config or runtime error

## Tests

```powershell
python -m unittest discover -s tests -v
```

## Notes

- YAML is optional because the MVP avoids external dependencies.
- DNS is resolved with built-in socket calls for A/AAAA and system resolver commands for other record types.
- In this sandbox, outbound sockets are blocked, so live HTTP and TLS smoke runs can fail here even though the code paths are valid.
- This is an MVP intended for GitHub and further extension, not a hardened production monitor yet.
