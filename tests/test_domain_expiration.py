import unittest
from unittest.mock import patch

from tests import _bootstrap  # noqa: F401
from domain_sentinel.checks.domain_expiration import extract_expiration_date, run_domain_expiration_check
from domain_sentinel.models import Defaults, SiteConfig


class DomainExpirationTests(unittest.TestCase):
    def test_marks_near_expiry_domain_as_critical(self) -> None:
        site = SiteConfig(
            id="main",
            domain="www.example.com",
            registered_domain="example.com",
            url="https://www.example.com/",
            redirect_url="http://www.example.com/",
            checks=["domain_expiration"],
        )
        payload = {
            "events": [
                {"eventAction": "registration", "eventDate": "2020-01-01T00:00:00Z"},
                {"eventAction": "expiration", "eventDate": "2026-04-01T00:00:00Z"},
            ]
        }
        defaults = Defaults(domain_warning_days=45, domain_critical_days=14)

        with patch(
            "domain_sentinel.checks.domain_expiration.fetch_rdap_document",
            return_value=payload,
        ):
            result = run_domain_expiration_check(site, defaults)

        self.assertEqual(result.status, "critical")
        self.assertEqual(result.details["registered_domain"], "example.com")
        self.assertIn("expires in", result.summary)

    def test_extracts_latest_expiration_event(self) -> None:
        payload = {
            "events": [
                {"eventAction": "expiration", "eventDate": "2027-01-01T00:00:00Z"},
                {"eventAction": "last update of RDAP database", "eventDate": "2026-01-01T00:00:00Z"},
                {"eventAction": "registry expiry", "eventDate": "2028-01-01T00:00:00Z"},
            ]
        }

        expires_at = extract_expiration_date(payload)

        self.assertIsNotNone(expires_at)
        self.assertEqual(expires_at.isoformat(), "2028-01-01T00:00:00+00:00")


if __name__ == "__main__":
    unittest.main()