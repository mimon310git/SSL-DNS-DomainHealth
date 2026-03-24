import unittest

from tests import _bootstrap  # noqa: F401
from domain_sentinel.diff import compare_snapshots


class DiffTests(unittest.TestCase):
    def test_detects_status_and_detail_changes(self) -> None:
        previous = {
            "site_results": [
                {
                    "id": "main",
                    "overall_status": "ok",
                    "checks": [
                        {
                            "name": "ssl",
                            "status": "ok",
                            "details": {
                                "expires_at": "2026-01-01T00:00:00+00:00",
                                "issuer": "CA-1",
                                "tls_version": "TLSv1.2",
                            },
                        },
                        {
                            "name": "dns",
                            "status": "ok",
                            "details": {"actual_records": {"A": ["192.0.2.10"]}},
                        },
                    ],
                }
            ]
        }
        current = {
            "site_results": [
                {
                    "id": "main",
                    "overall_status": "warning",
                    "checks": [
                        {
                            "name": "ssl",
                            "status": "warning",
                            "details": {
                                "expires_at": "2026-02-01T00:00:00+00:00",
                                "issuer": "CA-2",
                                "tls_version": "TLSv1.3",
                            },
                        },
                        {
                            "name": "dns",
                            "status": "warning",
                            "details": {"actual_records": {"A": ["192.0.2.11"]}},
                        },
                    ],
                }
            ]
        }

        changes = compare_snapshots(previous, current)
        self.assertIn("main", changes)
        self.assertTrue(any("Overall status changed" in message for message in changes["main"]))
        self.assertTrue(any("SSL expiry changed" in message for message in changes["main"]))
        self.assertTrue(any("A records changed" in message for message in changes["main"]))


if __name__ == "__main__":
    unittest.main()
