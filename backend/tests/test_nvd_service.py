import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database import Base
from app.db_models import VulnerabilityAffectedProduct, VulnerabilityRecord
from app.services.nvd_sync import sync_nvd_cves
from app.services.nvd_service import assess_stored_software, assess_software_against_nvd


class NvdServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def add_vulnerability(self, cve_id, score=8.8, minimum="2.4.0", maximum="2.4.49"):
        record = VulnerabilityRecord(
            cve_id=cve_id,
            description=f"Description for {cve_id}",
            severity="HIGH",
            cvss_score=score,
            affected_software="apache:http_server",
            min_version=minimum,
            max_version=maximum,
        )
        record.affected_products.append(VulnerabilityAffectedProduct(
            vendor="apache",
            product="http_server",
            affected_software="apache:http_server",
            min_version=minimum,
            max_version=maximum,
            min_version_inclusive=True,
            max_version_inclusive=True,
        ))
        self.session.add(record)
        self.session.commit()
        return record

    def test_stored_vulnerable_software_returns_full_match(self):
        self.add_vulnerability("CVE-2021-41773", score=9.8, minimum="2.4.49", maximum="2.4.49")

        result = assess_stored_software(self.session, "Apache HTTP Server", "2.4.49")

        self.assertEqual(result["matching_count"], 1)
        assessment = result["assessments"][0]
        self.assertTrue(assessment["matched"])
        self.assertEqual(assessment["cve_id"], "CVE-2021-41773")
        self.assertEqual(assessment["cvss_score"], 9.8)
        self.assertEqual(assessment["affected_products"][0]["max_version"], "2.4.49")

    def test_stored_non_vulnerable_version_is_not_matched(self):
        self.add_vulnerability("CVE-2021-41773", minimum="2.4.49", maximum="2.4.49")

        result = assess_stored_software(self.session, "Apache HTTP Server", "2.4.50")

        self.assertEqual(result["matching_count"], 0)
        self.assertFalse(result["assessments"][0]["matched"])

    def test_stored_multiple_cves_are_all_evaluated(self):
        self.add_vulnerability("CVE-2021-41773")
        self.add_vulnerability("CVE-2021-42013", score=9.0)

        result = assess_stored_software(self.session, "Apache HTTP Server", "2.4.49")

        self.assertEqual(result["result_count"], 2)
        self.assertEqual(result["matching_count"], 2)
        self.assertEqual({item["cve_id"] for item in result["assessments"]}, {"CVE-2021-41773", "CVE-2021-42013"})

    def test_missing_cvss_and_cpe_metadata_is_safe(self):
        self.session.add(VulnerabilityRecord(
            cve_id="CVE-2025-0001",
            description=None,
            severity=None,
            cvss_score=None,
            affected_software=None,
            min_version=None,
            max_version=None,
        ))
        self.session.commit()

        result = assess_stored_software(self.session, "Apache HTTP Server", "2.4.49")

        self.assertEqual(result["matching_count"], 0)
        self.assertIsNone(result["assessments"][0]["cvss_score"])
        self.assertEqual(result["assessments"][0]["affected_products"], [])

    @patch("app.services.nvd_service.search_cves")
    def test_nvd_results_are_matched_and_persisted_idempotently(self, search):
        search.return_value = [
            {
                "id": "CVE-2021-41773",
                "descriptions": [{"lang": "en", "value": "Apache path traversal"}],
                "metrics": {"cvssMetricV31": [{"cvssData": {"baseScore": 7.5, "baseSeverity": "HIGH"}}]},
                "configurations": [{"nodes": [{"cpeMatch": [{
                    "vulnerable": True,
                    "criteria": "cpe:2.3:a:apache:http_server:2.4.49:*:*:*:*:*:*:*",
                }]}]}],
            }
        ]

        first = assess_software_against_nvd(self.session, "Apache HTTP Server", "2.4.49")
        second = assess_software_against_nvd(self.session, "Apache HTTP Server", "2.4.49")

        self.assertEqual(first["result_count"], 1)
        self.assertTrue(first["assessments"][0]["matched"])
        self.assertEqual(first["assessments"][0]["risk_level"], "HIGH")
        self.assertEqual(second["result_count"], 1)
        records = self.session.query(VulnerabilityRecord).all()
        self.assertEqual(len(records), 1)
        self.assertEqual(len(records[0].affected_products), 1)

    @patch("app.services.nvd_sync.fetch_cves")
    def test_sync_reports_duplicates_and_missing_metadata(self, fetch):
        fetch.return_value = [
            {"id": "CVE-2025-0001", "descriptions": [], "metrics": {}, "configurations": []},
            {"id": "CVE-2025-0001", "descriptions": [], "metrics": {}, "configurations": []},
        ]

        summary = sync_nvd_cves(self.session, limit=2)

        self.assertEqual(summary, {
            "fetched": 2,
            "inserted": 1,
            "skipped_duplicates": 1,
            "failed": 0,
        })
        record = self.session.query(VulnerabilityRecord).one()
        self.assertIsNone(record.cvss_score)
        self.assertEqual(record.affected_products, [])


if __name__ == "__main__":
    unittest.main()
