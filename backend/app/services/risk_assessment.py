import math


def classify_risk(cvss_score: float | None) -> str:
    """Map CVSS score bands to a deterministic BREACH-X risk label."""
    if cvss_score is None:
        return "UNKNOWN"

    score = float(cvss_score)
    if not math.isfinite(score) or not 0.0 <= score <= 10.0:
        raise ValueError("CVSS score must be between 0.0 and 10.0")
    if score == 0.0:
        return "NONE"
    if score >= 9.0:
        return "CRITICAL"
    if score >= 7.0:
        return "HIGH"
    if score >= 4.0:
        return "MEDIUM"
    return "LOW"


def assess_risk(
    *,
    cve_id: str,
    affected_software: str,
    installed_version: str,
    matched: bool,
    cvss_score: float | None,
    original_severity: str | None,
) -> dict:
    """Build an asset-specific assessment from an existing match result.

    An unmatched product has no assessed exposure, so its risk is NONE.
    For a match with no CVSS score, the risk is UNKNOWN.
    """
    risk_level = classify_risk(cvss_score) if matched else "NONE"
    return {
        "cve_id": cve_id,
        "affected_software": affected_software,
        "installed_version": installed_version,
        "matched": matched,
        "cvss_score": cvss_score,
        "original_severity": original_severity,
        "risk_level": risk_level,
    }
