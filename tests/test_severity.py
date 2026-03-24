import unittest

from tests import _bootstrap  # noqa: F401
from domain_sentinel.severity import combine_statuses, exit_code_for_status


class SeverityTests(unittest.TestCase):
    def test_combine_statuses_uses_highest_severity(self) -> None:
        self.assertEqual(combine_statuses(["ok", "warning", "critical"]), "critical")
        self.assertEqual(combine_statuses(["ok", "warning"]), "warning")

    def test_exit_codes_match_status(self) -> None:
        self.assertEqual(exit_code_for_status("ok"), 0)
        self.assertEqual(exit_code_for_status("warning"), 1)
        self.assertEqual(exit_code_for_status("critical"), 2)


if __name__ == "__main__":
    unittest.main()
