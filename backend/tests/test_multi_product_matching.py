import unittest

from app.models.vulnerability import VulnerabilityMatchInfo, VulnerabilityMatchRequest
from app.services.cve_matcher import match_affected_products
from app.services.nvd_parser import parse_cve


class MultiProductMatchingTests(unittest.TestCase):
    products = [
        {
            "vendor": "apache",
            "product": "http_server",
            "affected_software": "apache:http_server",
            "min_version": "2.4.0",
            "max_version": "2.4.49",
            "min_version_inclusive": True,
            "max_version_inclusive": True,
        },
        {
            "vendor": "mozilla",
            "product": "firefox",
            "affected_software": "mozilla:firefox",
            "min_version": "132",
            "max_version": None,
            "min_version_inclusive": False,
            "max_version_inclusive": None,
        },
    ]

    def test_matches_first_product(self):
        self.assertTrue(match_affected_products("Apache HTTP Server", "2.4.49", self.products))

    def test_matches_later_product(self):
        self.assertTrue(match_affected_products("Firefox", "133", self.products))

    def test_no_product_match(self):
        self.assertFalse(match_affected_products("Thunderbird", "133", self.products))

    def test_product_match_with_version_outside_range(self):
        self.assertFalse(match_affected_products("Apache HTTP Server", "2.4.50", self.products))

    def test_parser_shaped_payload_is_accepted_by_match_request_model(self):
        request = VulnerabilityMatchRequest.model_validate(
            {
                "software_name": "Apache HTTP Server",
                "software_version": "2.4.49",
                "vulnerability": {
                    "cve_id": "CVE-2021-41773",
                    "description": "Apache HTTP Server path traversal",
                    "severity": "HIGH",
                    "cvss_score": 7.5,
                    "affected_products": [self.products[0], self.products[1]],
                },
            }
        )
        self.assertIsInstance(request.vulnerability, VulnerabilityMatchInfo)
        self.assertTrue(
            match_affected_products(
                request.software_name,
                request.software_version,
                request.vulnerability.affected_products,
            )
        )

    def test_actual_parser_product_shape_matches_human_software_name(self):
        parsed = parse_cve(
            {
                "id": "CVE-2021-41773",
                "descriptions": [{"lang": "en", "value": "Apache path traversal"}],
                "metrics": {},
                "configurations": [
                    {
                        "nodes": [
                            {
                                "cpeMatch": [
                                    {
                                        "vulnerable": True,
                                        "criteria": "cpe:2.3:a:apache:http_server:2.4.49:*:*:*:*:*:*:*",
                                    }
                                ]
                            }
                        ]
                    }
                ],
            }
        )
        self.assertEqual(parsed["affected_products"][0]["affected_software"], "apache:http_server")
        self.assertTrue(
            match_affected_products(
                "Apache HTTP Server", "2.4.49", parsed["affected_products"]
            )
        )

    def test_parser_treats_cpe_placeholder_version_as_open_ended(self):
        parsed = parse_cve(
            {
                "id": "CVE-2025-0001",
                "descriptions": [],
                "metrics": {},
                "configurations": [{"nodes": [{"cpeMatch": [{
                    "vulnerable": True,
                    "criteria": "cpe:2.3:a:vendor:product:-:*:*:*:*:*:*:*",
                }]}]}],
            }
        )
        product = parsed["affected_products"][0]
        self.assertIsNone(product["min_version"])
        self.assertIsNone(product["max_version"])

    def test_legacy_single_product_payload_remains_supported(self):
        request = VulnerabilityMatchRequest.model_validate(
            {
                "software_name": "Apache HTTP Server",
                "software_version": "2.4.49",
                "vulnerability": {
                    "cve_id": "CVE-2021-41773",
                    "description": "Apache HTTP Server path traversal",
                    "severity": "HIGH",
                    "cvss_score": 7.5,
                    "affected_software": "Apache HTTP Server",
                    "min_version": "2.4.49",
                    "max_version": "2.4.49",
                },
            }
        )
        vulnerability = request.vulnerability
        self.assertFalse(vulnerability.affected_products)
        self.assertEqual(vulnerability.affected_software, "Apache HTTP Server")
        self.assertTrue(vulnerability.min_version_inclusive)
        self.assertTrue(vulnerability.max_version_inclusive)


if __name__ == "__main__":
    unittest.main()
