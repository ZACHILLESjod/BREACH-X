"""NVD-backed software assessment orchestration."""

from sqlalchemy.orm import Session

from app.repositories.vulnerability_repository import list_vulnerabilities, upsert_normalized_vulnerability
from app.services.cve_matcher import match_affected_products, match_vulnerability
from app.services.nvd_client import search_cves
from app.services.nvd_parser import parse_cve
from app.services.risk_assessment import assess_risk


def _stored_match(software_name: str, software_version: str, vulnerability) -> bool:
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
        return match_affected_products(software_name, software_version, products)

    if not vulnerability.affected_software:
        return False

    return match_vulnerability(
        software_name,
        software_version,
        vulnerability.affected_software,
        vulnerability.min_version,
        vulnerability.max_version,
    )


def assess_stored_software(db: Session, software_name: str, software_version: str) -> dict:
    """Assess installed software against CVEs already stored from NVD."""
    assessments = []
    for vulnerability in list_vulnerabilities(db):
        matched = _stored_match(software_name, software_version, vulnerability)
        risk = assess_risk(
            cve_id=vulnerability.cve_id,
            affected_software=software_name,
            installed_version=software_version,
            matched=matched,
            cvss_score=vulnerability.cvss_score,
            original_severity=vulnerability.severity,
        )
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
        if not products and vulnerability.affected_software:
            products = [{
                "vendor": None,
                "product": vulnerability.affected_software,
                "edition": None,
                "affected_software": vulnerability.affected_software,
                "min_version": vulnerability.min_version,
                "max_version": vulnerability.max_version,
                "min_version_inclusive": True,
                "max_version_inclusive": True,
            }]
        assessments.append({
            **risk,
            "description": vulnerability.description,
            "affected_software": vulnerability.affected_software,
            "min_version": vulnerability.min_version,
            "max_version": vulnerability.max_version,
            "affected_products": products,
        })

    return {
        "software_name": software_name,
        "software_version": software_version,
        "result_count": len(assessments),
        "matching_count": sum(item["matched"] for item in assessments),
        "assessments": assessments,
    }


def assess_software_against_nvd(
    db: Session,
    software_name: str,
    software_version: str,
) -> dict:
    """Fetch, normalize, persist, and assess NVD CVEs for installed software."""
    raw_cves = search_cves(software_name, software_version)
    assessments = []

    for raw_cve in raw_cves:
        normalized = parse_cve(raw_cve)
        upsert_normalized_vulnerability(db, normalized)
        matched = match_affected_products(
            software_name,
            software_version,
            normalized.get("affected_products", []),
        )
        risk = assess_risk(
            cve_id=normalized["cve_id"],
            affected_software=software_name,
            installed_version=software_version,
            matched=matched,
            cvss_score=normalized.get("cvss_score"),
            original_severity=normalized.get("severity"),
        )
        assessments.append({
            **risk,
            "description": normalized.get("description"),
            "affected_products": normalized.get("affected_products", []),
        })

    return {
        "software_name": software_name,
        "software_version": software_version,
        "result_count": len(assessments),
        "assessments": assessments,
    }
