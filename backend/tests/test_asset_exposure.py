import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database import Base
from app.db_models import VulnerabilityAffectedProduct, VulnerabilityRecord
from app.models.asset import Asset
from app.models.software import Software
from app.models.vulnerability import Vulnerability
from app.repositories.asset_repository import save_asset, save_software
from app.services.asset_exposure import assess_asset_exposure


class AssetExposureTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        self.asset = Asset(
            asset_id="asset-1",
            hostname="host-1",
            ip_address="192.0.2.10",
            asset_type="server",
        )
        save_asset(self.session, self.asset)

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def add_software(self, software_id="software-1", name="Apache HTTP Server", version="2.4.49"):
        return save_software(
            self.session,
            Software(
                software_id=software_id,
                name=name,
                version=version,
                vendor="Apache",
                asset_id=self.asset.asset_id,
            ),
        )

    def add_vulnerability(
        self,
        cve_id="CVE-2024-10001",
        affected_software="Apache HTTP Server",
        minimum="2.4.0",
        maximum="2.4.49",
        score=8.5,
        severity="CRITICAL",
    ):
        record = VulnerabilityRecord(
            cve_id=cve_id,
            description="Unit test vulnerability",
            severity=severity,
            cvss_score=score,
            affected_software=affected_software,
            min_version=minimum,
            max_version=maximum,
        )
        self.session.add(record)
        self.session.commit()
        return record

    def test_asset_with_no_software_has_empty_exposures(self):
        result = assess_asset_exposure(self.session, self.asset.asset_id)
        self.assertEqual(result["software"], [])
        self.assertEqual(result["exposures"], [])
        self.assertEqual(result["summary"], {
            "total_software_checked": 0,
            "total_vulnerabilities_matched": 0,
            "highest_risk_level": "NONE",
            "total_exposed_software": 0,
        })

    def test_unaffected_software_is_reported_without_risk(self):
        self.add_software(name="Apache HTTP Server", version="2.4.50")
        self.add_vulnerability()

        result = assess_asset_exposure(self.session, self.asset.asset_id)
        exposure = result["exposures"][0]
        self.assertFalse(exposure["matched"])
        self.assertEqual(exposure["risk_level"], "NONE")
        self.assertEqual(result["summary"]["total_exposed_software"], 0)

    def test_vulnerable_software_matches_and_propagates_risk(self):
        self.add_software()
        self.add_vulnerability(score=8.5, severity="CRITICAL")

        result = assess_asset_exposure(self.session, self.asset.asset_id)
        exposure = result["exposures"][0]
        self.assertTrue(exposure["matched"])
        self.assertEqual(exposure["risk_level"], "HIGH")
        self.assertEqual(exposure["original_severity"], "CRITICAL")
        self.assertEqual(exposure["cvss_score"], 8.5)
        self.assertEqual(exposure["description"], "Unit test vulnerability")
        self.assertEqual(exposure["asset_id"], "asset-1")
        self.assertEqual(result["summary"]["highest_risk_level"], "HIGH")
        self.assertEqual(result["summary"]["total_exposed_software"], 1)

    def test_multiple_software_entries_are_assessed(self):
        self.add_software("software-1", "Apache HTTP Server", "2.4.49")
        self.add_software("software-2", "Unrelated Product", "1.0")
        self.add_vulnerability()

        result = assess_asset_exposure(self.session, self.asset.asset_id)
        self.assertEqual(len(result["software"]), 2)
        matches = {entry["software_id"]: entry["matched"] for entry in result["exposures"]}
        self.assertEqual(matches, {"software-1": True, "software-2": False})
        self.assertEqual(result["summary"]["total_software_checked"], 2)
        self.assertEqual(result["summary"]["total_exposed_software"], 1)

    def test_multiple_vulnerable_software_packages_are_counted(self):
        self.add_software("software-1", "Apache HTTP Server", "2.4.49")
        self.add_software("software-2", "Apache HTTP Server", "2.4.48")
        self.add_vulnerability(minimum="2.4.0", maximum="2.4.49")

        result = assess_asset_exposure(self.session, self.asset.asset_id)

        self.assertEqual(result["summary"]["total_software_checked"], 2)
        self.assertEqual(result["summary"]["total_vulnerabilities_matched"], 2)
        self.assertEqual(result["summary"]["total_exposed_software"], 2)

    def test_multiple_vulnerabilities_are_assessed(self):
        self.add_software()
        self.add_vulnerability("CVE-2024-10001", score=9.1, severity="CRITICAL")
        self.add_vulnerability(
            "CVE-2024-10002", "Other Software", "1.0", "2.0", 6.0, "MEDIUM"
        )

        result = assess_asset_exposure(self.session, self.asset.asset_id)
        by_cve = {entry["cve_id"]: entry for entry in result["exposures"]}
        self.assertEqual(len(by_cve), 2)
        self.assertTrue(by_cve["CVE-2024-10001"]["matched"])
        self.assertEqual(by_cve["CVE-2024-10001"]["risk_level"], "CRITICAL")
        self.assertFalse(by_cve["CVE-2024-10002"]["matched"])
        self.assertEqual(result["summary"]["total_vulnerabilities_matched"], 1)

    def test_multiple_cves_affecting_one_software_are_returned(self):
        self.add_software()
        self.add_vulnerability("CVE-2024-10001", score=8.0)
        self.add_vulnerability("CVE-2024-10002", score=9.1, severity="CRITICAL")

        result = assess_asset_exposure(self.session, self.asset.asset_id)

        matched = [exposure for exposure in result["exposures"] if exposure["matched"]]
        self.assertEqual({exposure["cve_id"] for exposure in matched}, {
            "CVE-2024-10001", "CVE-2024-10002"
        })
        self.assertEqual(result["summary"]["total_exposed_software"], 1)
        self.assertEqual(result["summary"]["highest_risk_level"], "CRITICAL")

    def test_affected_product_relationship_is_used_when_present(self):
        self.add_software("software-1", "Firefox", "133")
        vulnerability = self.add_vulnerability(
            affected_software="legacy-other-product", minimum="1", maximum="1"
        )
        self.session.add(
            VulnerabilityAffectedProduct(
                vulnerability_id=vulnerability.id,
                vendor="mozilla",
                product="firefox",
                affected_software="mozilla:firefox",
                min_version="132",
                max_version=None,
                min_version_inclusive=False,
                max_version_inclusive=None,
            )
        )
        self.session.commit()

        result = assess_asset_exposure(self.session, self.asset.asset_id)
        self.assertTrue(result["exposures"][0]["matched"])

    def test_missing_cvss_and_cpe_metadata_is_safe(self):
        self.add_software()
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

        result = assess_asset_exposure(self.session, self.asset.asset_id)

        exposure = result["exposures"][0]
        self.assertFalse(exposure["matched"])
        self.assertIsNone(exposure["cvss_score"])
        self.assertIsNone(exposure["description"])
        self.assertEqual(result["summary"]["highest_risk_level"], "NONE")


if __name__ == "__main__":
    unittest.main()
