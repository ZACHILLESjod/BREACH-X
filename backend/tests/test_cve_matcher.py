import unittest

from app.services.cve_matcher import match_vulnerability


class MatchVulnerabilityTests(unittest.TestCase):
    def match(self, installed, minimum="2.4.0", maximum="2.4.49", **kwargs):
        return match_vulnerability(
            "Apache HTTP Server",
            installed,
            "Apache HTTP Server",
            minimum,
            maximum,
            **kwargs,
        )

    def test_real_cve_exact_affected_release(self):
        # CVE-2021-41773 affected Apache HTTP Server 2.4.49.
        self.assertTrue(self.match("2.4.49", "2.4.49", "2.4.49"))

    def test_below_and_above_range(self):
        self.assertFalse(self.match("2.3.99"))
        self.assertFalse(self.match("2.4.50"))

    def test_software_name_mismatch(self):
        self.assertFalse(
            match_vulnerability("Apache Tomcat", "2.4.49", "Apache HTTP Server", "2.4.0", "2.4.49")
        )

    def test_range_endpoints_are_inclusive_by_default(self):
        self.assertTrue(self.match("2.4.0"))
        self.assertTrue(self.match("2.4.49"))

    def test_exclusive_boundaries_are_respected(self):
        self.assertFalse(self.match("2.4.0", min_version_inclusive=False))
        self.assertFalse(self.match("2.4.49", max_version_inclusive=False))

    def test_semantic_numeric_and_trailing_zero_comparison(self):
        self.assertTrue(self.match("2.4.9", "2.4.0", "2.4.10"))
        self.assertTrue(self.match("2.4", "2.4.0", "2.4.0"))
        self.assertFalse(self.match("2.4.10", "2.4.0", "2.4.9"))

    def test_prerelease_sorts_before_stable(self):
        self.assertFalse(self.match("2.4.49-rc1", "2.4.49", "2.4.50"))
        self.assertTrue(self.match("2.4.49-rc1", "2.4.48", "2.4.49"))

    def test_unparseable_version_does_not_crash(self):
        self.assertFalse(self.match("unknown"))


if __name__ == "__main__":
    unittest.main()
