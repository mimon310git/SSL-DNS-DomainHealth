import json
import shutil
import unittest
from pathlib import Path

from tests import _bootstrap  # noqa: F401
from domain_sentinel.config import load_config

ROOT = Path(__file__).resolve().parents[1]
TEST_ROOT = ROOT / ".test-tmp"


class ConfigTests(unittest.TestCase):
    def test_loads_json_and_normalizes_expectations(self) -> None:
        payload = {
            "version": 1,
            "sites": [
                {
                    "id": "site-1",
                    "domain": "example.com",
                    "expected_status": 200,
                    "expected_contains": "ok",
                    "expected_redirect_to": "https://www.example.com/",
                    "dns": {"ns": ["ns1.example.com"]},
                }
            ],
        }
        workdir = TEST_ROOT / "config-load"
        shutil.rmtree(workdir, ignore_errors=True)
        workdir.mkdir(parents=True, exist_ok=True)
        path = workdir / "config.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        config = load_config(path)

        site = config.sites[0]
        self.assertEqual(site.expect["status_code"], 200)
        self.assertEqual(site.expect["body_contains"], "ok")
        self.assertEqual(site.expect["final_url"], "https://www.example.com/")
        self.assertEqual(site.expect["dns"]["NS"], ["ns1.example.com"])
        self.assertEqual(site.url, "https://example.com/")
        self.assertEqual(site.redirect_url, "http://example.com/")

    def test_rejects_duplicate_site_ids(self) -> None:
        payload = {
            "sites": [
                {"id": "same", "domain": "a.example.com"},
                {"id": "same", "domain": "b.example.com"},
            ]
        }
        workdir = TEST_ROOT / "config-duplicates"
        shutil.rmtree(workdir, ignore_errors=True)
        workdir.mkdir(parents=True, exist_ok=True)
        path = workdir / "config.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaises(ValueError):
            load_config(path)


if __name__ == "__main__":
    unittest.main()
