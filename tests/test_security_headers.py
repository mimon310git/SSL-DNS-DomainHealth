import unittest
from unittest.mock import patch

from tests import _bootstrap  # noqa: F401
from domain_sentinel.checks.security_headers import run_security_headers_check
from domain_sentinel.models import Defaults, SiteConfig


class SecurityHeadersTests(unittest.TestCase):
    def test_warns_on_missing_headers(self) -> None:
        site = SiteConfig(
            id="main",
            domain="example.com",
            registered_domain="example.com",
            url="https://example.com/",
            redirect_url="http://example.com/",
            checks=["security_headers"],
        )
        response = {
            "status_code": 200,
            "final_url": "https://example.com/",
            "headers": {
                "Content-Security-Policy": "default-src 'self'",
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "SAMEORIGIN",
            },
        }

        with patch("domain_sentinel.checks.security_headers.fetch_url", return_value=response):
            result = run_security_headers_check(site, Defaults())

        self.assertEqual(result.status, "warning")
        self.assertIn("Strict-Transport-Security", result.details["missing_headers"])

    def test_warns_on_invalid_header_values(self) -> None:
        site = SiteConfig(
            id="main",
            domain="example.com",
            registered_domain="example.com",
            url="https://example.com/",
            redirect_url="http://example.com/",
            checks=["security_headers"],
        )
        response = {
            "status_code": 200,
            "final_url": "https://example.com/",
            "headers": {
                "Strict-Transport-Security": "includeSubDomains",
                "Content-Security-Policy": "default-src 'self'",
                "X-Content-Type-Options": "allow",
                "X-Frame-Options": "ALLOWALL",
            },
        }

        with patch("domain_sentinel.checks.security_headers.fetch_url", return_value=response):
            result = run_security_headers_check(site, Defaults())

        self.assertEqual(result.status, "warning")
        self.assertTrue(any("X-Content-Type-Options" in item for item in result.details["invalid_headers"]))
        self.assertTrue(any("X-Frame-Options" in item for item in result.details["invalid_headers"]))


if __name__ == "__main__":
    unittest.main()