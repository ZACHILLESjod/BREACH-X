import unittest

from app.services.risk_assessment import assess_risk, classify_risk


class RiskClassificationTests(unittest.TestCase):
    def test_cvss_score_bands(self):
        cases = (
            (10.0, "CRITICAL"),
            (9.0, "CRITICAL"),
            (8.9, "HIGH"),
            (7.0, "HIGH"),
            (6.9, "MEDIUM"),
            (4.0, "MEDIUM"),
            (3.9, "LOW"),
            (0.0, "NONE"),
            (None, "UNKNOWN"),
        )
        for score, expected in cases:
            with self.subTest(score=score):
                self.assertEqual(classify_risk(score), expected)

    def test_matched_software_gets_score_based_risk_and_original_severity(self):
        result = assess_risk(
            cve_id="CVE-2024-3094",
            affected_software="xz",
            installed_version="5.6.1",
            matched=True,
            cvss_score=10.0,
            original_severity="CRITICAL",
        )
        self.assertEqual(result["risk_level"], "CRITICAL")
        self.assertEqual(result["original_severity"], "CRITICAL")
        self.assertTrue(result["matched"])
        self.assertEqual(result["installed_version"], "5.6.1")

    def test_unmatched_software_has_no_assessed_risk(self):
        result = assess_risk(
            cve_id="CVE-2024-3094",
            affected_software="unrelated software",
            installed_version="1.0",
            matched=False,
            cvss_score=10.0,
            original_severity="CRITICAL",
        )
        self.assertEqual(result["risk_level"], "NONE")
        self.assertFalse(result["matched"])
        self.assertEqual(result["cvss_score"], 10.0)
        self.assertEqual(result["original_severity"], "CRITICAL")

    def test_matched_without_score_is_unknown(self):
        result = assess_risk(
            cve_id="CVE-UNKNOWN-SCORE",
            affected_software="Example Software",
            installed_version="1.0",
            matched=True,
            cvss_score=None,
            original_severity="HIGH",
        )
        self.assertEqual(result["risk_level"], "UNKNOWN")

    def test_out_of_range_score_is_rejected(self):
        with self.assertRaises(ValueError):
            classify_risk(10.1)


if __name__ == "__main__":
    unittest.main()
