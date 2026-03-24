import unittest

from tests import _bootstrap  # noqa: F401
from domain_sentinel.checks.ssl import evaluate_certificate
from domain_sentinel.models import Defaults


class SSLTests(unittest.TestCase):
    def test_marks_hostname_mismatch_as_critical(self) -> None:
        certificate = {
            "notAfter": "Jan 01 00:00:00 2030 GMT",
            "subject": ((("commonName", "example.com"),),),
            "issuer": ((("commonName", "Test CA"),),),
            "subjectAltName": (("DNS", "example.com"),),
        }
        status, issues, details = evaluate_certificate(
            "api.example.com", 443, certificate, "TLSv1.3", Defaults()
        )

        self.assertEqual(status, "critical")
        self.assertTrue(details["hostname_mismatch"])
        self.assertTrue(any("hostname mismatch" in issue for issue in issues))

    def test_marks_self_signed_as_critical(self) -> None:
        certificate = {
            "notAfter": "Jan 01 00:00:00 2030 GMT",
            "subject": ((("commonName", "example.com"),),),
            "issuer": ((("commonName", "example.com"),),),
            "subjectAltName": (("DNS", "example.com"),),
        }
        status, issues, details = evaluate_certificate(
            "example.com", 443, certificate, "TLSv1.3", Defaults()
        )

        self.assertEqual(status, "critical")
        self.assertTrue(details["self_signed"])
        self.assertTrue(any("self-signed" in issue for issue in issues))

    def test_marks_legacy_tls_as_critical(self) -> None:
        certificate = {
            "notAfter": "Jan 01 00:00:00 2030 GMT",
            "subject": ((("commonName", "example.com"),),),
            "issuer": ((("commonName", "Test CA"),),),
            "subjectAltName": (("DNS", "example.com"),),
        }
        status, issues, _ = evaluate_certificate(
            "example.com", 443, certificate, "TLSv1.1", Defaults()
        )

        self.assertEqual(status, "critical")
        self.assertTrue(any("legacy TLS version" in issue for issue in issues))


if __name__ == "__main__":
    unittest.main()
