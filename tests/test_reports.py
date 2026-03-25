import csv
import shutil
import unittest
from pathlib import Path

from tests import _bootstrap  # noqa: F401
from domain_sentinel.models import CheckResult, RunSummary, SiteResult, Snapshot
from domain_sentinel.report.csv_report import write_csv_report
from domain_sentinel.report.html_report import write_html_report

ROOT = Path(__file__).resolve().parents[1]
TEST_ROOT = ROOT / ".test-tmp"


class ReportTests(unittest.TestCase):
    def _snapshot(self) -> Snapshot:
        return Snapshot(
            generated_at="2026-03-24T10:00:00+00:00",
            config_path="config.json",
            summary=RunSummary(
                overall_status="warning",
                total_sites=1,
                ok_sites=0,
                warning_sites=1,
                critical_sites=0,
            ),
            site_results=[
                SiteResult(
                    id="main",
                    domain="example.com",
                    url="https://example.com/",
                    tags=["prod"],
                    overall_status="warning",
                    checks=[
                        CheckResult("ssl", "warning", "soon", {"days_to_expiry": 5}),
                        CheckResult(
                            "domain_expiration",
                            "ok",
                            "long enough",
                            {"days_to_expiry": 180},
                        ),
                        CheckResult("http", "ok", "good", {"status_code": 200, "response_ms": 120}),
                        CheckResult(
                            "security_headers",
                            "warning",
                            "missing HSTS",
                            {"missing_headers": ["Strict-Transport-Security"]},
                        ),
                    ],
                    changes=["something changed"],
                )
            ],
        )

    def test_writes_csv_summary(self) -> None:
        snapshot = self._snapshot()
        workdir = TEST_ROOT / "csv-report"
        shutil.rmtree(workdir, ignore_errors=True)
        workdir.mkdir(parents=True, exist_ok=True)
        path = workdir / "latest.csv"
        write_csv_report(snapshot, path)
        with path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["site_id"], "main")
        self.assertEqual(rows[0]["ssl_days_to_expiry"], "5")
        self.assertEqual(rows[0]["domain_days_to_expiry"], "180")
        self.assertEqual(rows[0]["security_headers_status"], "warning")
        self.assertEqual(rows[0]["missing_security_headers"], "Strict-Transport-Security")
        self.assertEqual(rows[0]["change_count"], "1")

    def test_writes_html_report(self) -> None:
        snapshot = self._snapshot()
        workdir = TEST_ROOT / "html-report"
        shutil.rmtree(workdir, ignore_errors=True)
        workdir.mkdir(parents=True, exist_ok=True)
        path = workdir / "latest.html"
        write_html_report(snapshot, path)
        content = path.read_text(encoding="utf-8")

        self.assertIn("Domain Sentinel Report", content)
        self.assertIn("main", content)
        self.assertIn("something changed", content)


if __name__ == "__main__":
    unittest.main()