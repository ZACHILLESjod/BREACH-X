"""Normalize a single NVD CVE API 2.0 response for BREACH-X."""

from typing import Any, Iterator


def _walk_matches(value: Any) -> Iterator[dict]:
    """Yield CPE match objects recursively from NVD configuration nodes."""
    if isinstance(value, dict):
        for match in value.get("cpeMatch", []):
            if isinstance(match, dict):
                yield match
        for key, child in value.items():
            if key != "cpeMatch":
                yield from _walk_matches(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_matches(child)


def _first_cvss(cve: dict) -> tuple[str | None, float | None]:
    metrics = cve.get("metrics", {})
    for metric_name in ("cvssMetricV31", "cvssMetricV30"):
        entries = metrics.get(metric_name, [])
        for entry in entries:
            data = entry.get("cvssData", {})
            if data.get("baseScore") is not None:
                severity = data.get("baseSeverity") or entry.get("baseSeverity")
                return severity, data["baseScore"]
    return None, None


def parse_cve(raw: dict) -> dict:
    """Return BREACH-X fields and every valid vulnerable CPE match.

    Each CPE match is retained as an independent entry. Configuration
    conditions are deliberately not evaluated here.
    """
    vulnerabilities = raw.get("vulnerabilities")
    if vulnerabilities is not None:
        if not vulnerabilities:
            raise ValueError("NVD response contains no vulnerabilities")
        cve = vulnerabilities[0].get("cve", {})
    else:
        # get_cve() returns the individual CVE object rather than its envelope.
        cve = raw
    if not isinstance(cve, dict) or not cve.get("id"):
        raise ValueError("NVD response does not contain a valid CVE object")
    descriptions = cve.get("descriptions", [])
    description = next(
        (item.get("value") for item in descriptions if item.get("lang") == "en"),
        None,
    )
    severity, score = _first_cvss(cve)

    affected_products = []
    for match in _walk_matches(cve.get("configurations", [])):
        if match.get("vulnerable") is not True:
            continue
        criteria = match.get("criteria", "")
        parts = criteria.split(":")
        if len(parts) < 6 or parts[0] != "cpe" or parts[1] != "2.3":
            continue

        vendor, product = parts[3], parts[4]
        if not vendor or not product or vendor == "*" or product == "*":
            continue
        # CPE 2.3 can encode product variants in sw_edition. Mozilla's Firefox
        # ESR match uses sw_edition "esr" while normal Firefox uses "*".
        edition = parts[9] if len(parts) > 9 and parts[9] not in ("*", "-") else None

        entry = {
            "vendor": vendor,
            "product": product,
            "edition": edition,
            "affected_software": f"{vendor}:{product}" + (f":{edition}" if edition else ""),
            "min_version": None,
            "max_version": None,
            "min_version_inclusive": None,
            "max_version_inclusive": None,
        }

        start_including = match.get("versionStartIncluding")
        start_excluding = match.get("versionStartExcluding")
        end_including = match.get("versionEndIncluding")
        end_excluding = match.get("versionEndExcluding")
        cpe_version = parts[5]

        if start_including is not None:
            entry["min_version"] = start_including
            entry["min_version_inclusive"] = True
        elif start_excluding is not None:
            entry["min_version"] = start_excluding
            entry["min_version_inclusive"] = False
        elif cpe_version not in ("*", "-"):
            entry["min_version"] = cpe_version
            entry["min_version_inclusive"] = True

        if end_including is not None:
            entry["max_version"] = end_including
            entry["max_version_inclusive"] = True
        elif end_excluding is not None:
            entry["max_version"] = end_excluding
            entry["max_version_inclusive"] = False
        elif cpe_version not in ("*", "-") and entry["min_version"] == cpe_version:
            entry["max_version"] = cpe_version
            entry["max_version_inclusive"] = True

        affected_products.append(entry)

    return {
        "cve_id": cve.get("id"),
        "description": description,
        "severity": severity,
        "cvss_score": score,
        "affected_products": affected_products,
    }
