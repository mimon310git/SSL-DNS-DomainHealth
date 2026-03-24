# Domain Sentinel

Domain Sentinel is a small multi-site SSL, DNS, redirect, and endpoint health manager built as a portfolio-ready ops utility.

## What it does

- checks SSL certificate expiry and basic TLS details
- checks DNS records against expected values or basic resolvability
- checks redirect behavior and loop risk
- checks HTTP endpoint status, content, and latency threshold
- stores a snapshot from each run
- compares the latest run against the previous run
- exports JSON and CSV reports

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
