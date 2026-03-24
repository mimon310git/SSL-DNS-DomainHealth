import csv
import shutil
import unittest
from pathlib import Path

from tests import _bootstrap  # noqa: F401
from domain_sentinel.models import CheckResult, RunSummary, SiteResult, Snapshot
from domain_sentinel.report.csv_report import write_csv_report

ROOT = Path(__file__).resolve().parents[1]
TEST_ROOT = ROOT / ".test-tmp"


class ReportTests(unittest.TestCase):
    def test_writes_csv_summary(self) -> None:
        snapshot = Snapshot(
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
                        CheckResult("http", "ok", "good", {"status_code": 200, "response_ms": 120}),
                    ],
                    changes=["something changed"],
                )
            ],
        )
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
        self.assertEqual(rows[0]["change_count"], "1")


if __name__ == "__main__":
    unittest.main()
