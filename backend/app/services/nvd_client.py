"""Small client for looking up a single CVE in the NVD CVE API 2.0."""

import os

import requests


NVD_CVE_API_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"
NVD_TIMEOUT_SECONDS = 30


def _request_headers() -> dict[str, str]:
    api_key = os.getenv("NVD_API_KEY")
    return {"apiKey": api_key} if api_key else {}


def fetch_cve(cve_id: str) -> dict:
    """Fetch the raw NVD CVE API 2.0 response for *cve_id*."""
    response = requests.get(
        NVD_CVE_API_URL,
        params={"cveId": cve_id},
        headers=_request_headers(),
        timeout=NVD_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()


def get_cve(cve_id: str) -> dict | None:
    """Return the CVE object for *cve_id*, or ``None`` when it does not exist.

    Request and HTTP errors are intentionally allowed to propagate so the API
    layer can translate upstream failures into appropriate HTTP responses.
    """
    try:
        payload = fetch_cve(cve_id)
    except requests.exceptions.JSONDecodeError as error:
        raise ValueError("NVD returned invalid JSON") from error
    except requests.exceptions.HTTPError as error:
        # NVD returns HTTP 404 for an unknown cveId rather than an empty
        # successful response. Treat that as an absent CVE; propagate all
        # other HTTP errors for the API layer to report as upstream failures.
        if error.response is not None and error.response.status_code == 404:
            return None
        raise
    if not isinstance(payload, dict):
        raise ValueError("NVD returned an invalid response")
    vulnerabilities = payload.get("vulnerabilities")
    total_results = payload.get("totalResults")
    if not isinstance(vulnerabilities, list) or not isinstance(total_results, int):
        raise ValueError("NVD response is missing its results fields")
    if total_results == 0:
        if vulnerabilities:
            raise ValueError("NVD response has inconsistent result counts")
        return None
    if not vulnerabilities:
        raise ValueError("NVD response reports results but contains no CVE")

    first_result = vulnerabilities[0]
    cve = first_result.get("cve") if isinstance(first_result, dict) else None
    if not isinstance(cve, dict) or not isinstance(cve.get("id"), str):
        raise ValueError("NVD response does not contain a valid CVE object")
    if cve["id"].upper() != cve_id.upper():
        raise ValueError("NVD returned a different CVE than requested")
    return cve


def search_cves(software_name: str, software_version: str) -> list[dict]:
    """Search NVD CVE 2.0 for software/version keywords.

    NVD's keyword search is intentionally used instead of constructing a CPE
    locally, because installed software names may not map cleanly to one CPE.
    The parser and matcher perform the authoritative CPE/version assessment.
    """
    response = requests.get(
        NVD_CVE_API_URL,
        params={
            "keywordSearch": f"{software_name} {software_version}",
            "resultsPerPage": 2000,
        },
        headers=_request_headers(),
        timeout=NVD_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    try:
        payload = response.json()
    except requests.exceptions.JSONDecodeError as error:
        raise ValueError("NVD returned invalid JSON") from error
    if not isinstance(payload, dict):
        raise ValueError("NVD returned an invalid response")
    vulnerabilities = payload.get("vulnerabilities")
    if not isinstance(vulnerabilities, list):
        raise ValueError("NVD response is missing its vulnerability results")

    results = []
    seen = set()
    for item in vulnerabilities:
        cve = item.get("cve") if isinstance(item, dict) else None
        cve_id = cve.get("id") if isinstance(cve, dict) else None
        if isinstance(cve_id, str) and cve_id not in seen:
            results.append(cve)
            seen.add(cve_id)
    return results


def fetch_cves(limit: int = 10) -> list[dict]:
    """Fetch a small, recent page of CVEs from NVD CVE API 2.0."""
    if not 1 <= limit <= 2000:
        raise ValueError("NVD CVE limit must be between 1 and 2000")

    response = requests.get(
        NVD_CVE_API_URL,
        params={"resultsPerPage": limit, "startIndex": 0},
        headers=_request_headers(),
        timeout=NVD_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    try:
        payload = response.json()
    except requests.exceptions.JSONDecodeError as error:
        raise ValueError("NVD returned invalid JSON") from error
    if not isinstance(payload, dict):
        raise ValueError("NVD returned an invalid response")

    vulnerabilities = payload.get("vulnerabilities")
    if not isinstance(vulnerabilities, list):
        raise ValueError("NVD response is missing its vulnerability results")

    results = []
    seen = set()
    for item in vulnerabilities[:limit]:
        cve = item.get("cve") if isinstance(item, dict) else None
        cve_id = cve.get("id") if isinstance(cve, dict) else None
        if isinstance(cve_id, str) and cve_id.upper() not in seen:
            results.append(cve)
            seen.add(cve_id.upper())
    return results
