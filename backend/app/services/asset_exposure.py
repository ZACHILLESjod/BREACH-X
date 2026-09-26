from sqlalchemy.orm import Session

from app.db_models import VulnerabilityRecord
from app.repositories.asset_repository import get_asset_with_software
from app.repositories.vulnerability_repository import list_vulnerabilities
from app.services.cve_matcher import match_affected_products, match_vulnerability
from app.services.risk_assessment import assess_risk


def _matches_vulnerability(software, vulnerability: VulnerabilityRecord) -> bool:
    if vulnerability.affected_products:
        products = [
            {
                "vendor": product.vendor,
                "product": product.product,
                "edition": product.edition,
                "affected_software": product.affected_software,
                "min_version": product.min_version,
                "max_version": product.max_version,
                "min_version_inclusive": product.min_version_inclusive,
                "max_version_inclusive": product.max_version_inclusive,
            }
            for product in vulnerability.affected_products
        ]
        return match_affected_products(software.name, software.version, products)

    if not vulnerability.affected_software:
        return False

    return match_vulnerability(
        software.name,
        software.version,
        vulnerability.affected_software,
        vulnerability.min_version,
        vulnerability.max_version,
    )


def assess_asset_exposure(db: Session, asset_id: str) -> dict | None:
    """Assess every installed-software/local-CVE pair for one asset."""
    asset = get_asset_with_software(db, asset_id)
    if asset is None:
        return None

    vulnerabilities = list_vulnerabilities(db)
    software_entries = []
    exposures = []
    risk_order = {"UNKNOWN": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}

    for software in asset.software:
        software_entries.append(
            {
                "software_id": software.software_id,
                "name": software.name,
                "version": software.version,
                "vendor": software.vendor,
            }
        )
        for vulnerability in vulnerabilities:
            matched = _matches_vulnerability(software, vulnerability)
            result = assess_risk(
                cve_id=vulnerability.cve_id,
                affected_software=software.name,
                installed_version=software.version,
                matched=matched,
                cvss_score=vulnerability.cvss_score,
                original_severity=vulnerability.severity,
            )
            result["software_id"] = software.software_id
            result["vendor"] = software.vendor
            result["asset_id"] = asset.asset_id
            result["asset_hostname"] = asset.hostname
            result["asset_type"] = asset.asset_type
            result["severity"] = vulnerability.severity
            result["description"] = vulnerability.description
            result["min_version"] = vulnerability.min_version
            result["max_version"] = vulnerability.max_version
            result["affected_products"] = [
                {
                    "vendor": product.vendor,
                    "product": product.product,
                    "edition": product.edition,
                    "affected_software": product.affected_software,
                    "min_version": product.min_version,
                    "max_version": product.max_version,
                    "min_version_inclusive": product.min_version_inclusive,
                    "max_version_inclusive": product.max_version_inclusive,
                }
                for product in vulnerability.affected_products
            ]
            exposures.append(result)

    matched_exposures = [exposure for exposure in exposures if exposure["matched"]]
    highest_risk = max(
        (exposure["risk_level"] for exposure in matched_exposures),
        key=lambda level: risk_order.get(level, 0),
        default="NONE",
    )
    exposed_software = {
        exposure["software_id"]
        for exposure in matched_exposures
    }

    return {
        "asset": {
            "asset_id": asset.asset_id,
            "hostname": asset.hostname,
            "ip_address": asset.ip_address,
            "asset_type": asset.asset_type,
            "operating_system": asset.operating_system,
            "criticality": asset.criticality,
        },
        "software": software_entries,
        "exposures": exposures,
        "summary": {
            "total_software_checked": len(software_entries),
            "total_vulnerabilities_matched": len(matched_exposures),
            "highest_risk_level": highest_risk,
            "total_exposed_software": len(exposed_software),
        },
    }
