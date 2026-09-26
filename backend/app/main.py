import os
import requests
import secrets
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import engine, get_db
from app.models.asset import Asset
from app.models.software import Software
from app.models.vulnerability import NvdAssessRequest, Vulnerability, VulnerabilityMatchRequest
from app.repositories.vulnerability_repository import (
    create_vulnerability as persist_vulnerability,
    get_vulnerability_by_cve_id,
)
from app.repositories.asset_repository import list_assets, save_asset, save_software
from app.services.asset_exposure import assess_asset_exposure
from app.services.cve_matcher import match_affected_products, match_vulnerability
from app.services.nvd_client import get_cve
from app.services.nvd_parser import parse_cve
from app.services.nvd_service import assess_stored_software
from app.services.nvd_sync import sync_nvd_cves
from app.services.risk_assessment import assess_risk

app = FastAPI(title="BREACHX")

cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]
if "*" in cors_origins:
    raise RuntimeError("CORS_ORIGINS must list exact origins; wildcard origins are not supported.")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-API-Key"],
)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(api_key: str | None = Depends(api_key_header)) -> None:
    configured_key = os.getenv("BREACHX_API_KEY")
    if not configured_key:
        raise HTTPException(
            status_code=503,
            detail="API key protection is not configured.",
        )
    if not api_key or not secrets.compare_digest(
        api_key.encode("utf-8"), configured_key.encode("utf-8")
    ):
        raise HTTPException(status_code=401, detail="A valid X-API-Key is required.")


@app.get("/")
def home():
    return {
        "project": "BREACHX",
        "status": "online",
        "message": "BREACHX backend is running"
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/db")
def database_health():
    if engine is None:
        raise HTTPException(status_code=503, detail="Database is not configured.")
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as error:
        raise HTTPException(status_code=503, detail="Database is unavailable.") from error
    return {"status": "ok", "database": "connected"}


@app.post("/assets", dependencies=[Depends(require_api_key)])
def create_asset(asset: Asset, db: Session | None = Depends(get_db)):
    if db is None:
        raise HTTPException(status_code=503, detail="Database is not configured.")
    try:
        save_asset(db, asset)
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(status_code=503, detail="Unable to store asset.") from error
    return {
        "message": "Asset registered successfully",
        "asset": asset
    }


@app.get("/assets")
def get_assets(db: Session | None = Depends(get_db)):
    if db is None:
        raise HTTPException(status_code=503, detail="Database is not configured.")
    try:
        assets = list_assets(db)
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(status_code=503, detail="Unable to list assets.") from error

    return [
        {
            "asset_id": asset.asset_id,
            "hostname": asset.hostname,
            "ip_address": asset.ip_address,
            "asset_type": asset.asset_type,
            "operating_system": asset.operating_system,
            "criticality": asset.criticality,
        }
        for asset in assets
    ]


@app.post("/software", dependencies=[Depends(require_api_key)])
def create_software(software: Software, db: Session | None = Depends(get_db)):
    if db is None:
        raise HTTPException(status_code=503, detail="Database is not configured.")
    try:
        record = save_software(db, software)
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(status_code=503, detail="Unable to store software.") from error
    if record is None:
        raise HTTPException(status_code=404, detail="Asset not found.")
    return {
        "message": "Software registered successfully",
        "software": software
    }


@app.get("/assets/{asset_id}/exposure")
def get_asset_exposure(asset_id: str, db: Session | None = Depends(get_db)):
    if db is None:
        raise HTTPException(status_code=503, detail="Database is not configured.")
    try:
        exposure = assess_asset_exposure(db, asset_id)
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(
            status_code=503,
            detail="Unable to assess asset exposure.",
        ) from error
    if exposure is None:
        raise HTTPException(status_code=404, detail="Asset not found.")
    return exposure

@app.post("/vulnerabilities", dependencies=[Depends(require_api_key)])
def create_vulnerability(
    vulnerability: Vulnerability,
    db: Session | None = Depends(get_db),
):
    if db is None:
        raise HTTPException(
            status_code=503,
            detail="Database is not configured.",
        )

    try:
        record = persist_vulnerability(db, vulnerability)
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(
            status_code=503,
            detail="Unable to persist vulnerability.",
        ) from error

    return {
        "message": "Vulnerability stored successfully",
        "database_id": record.id,
        "vulnerability": vulnerability,
    }


@app.get("/cve/{cve_id}", dependencies=[Depends(require_api_key)])
def lookup_cve(cve_id: str, db: Session | None = Depends(get_db)):
    if db is not None:
        try:
            stored_vulnerability = get_vulnerability_by_cve_id(db, cve_id)
        except SQLAlchemyError as error:
            db.rollback()
            raise HTTPException(
                status_code=503,
                detail="Unable to query stored vulnerability.",
            ) from error

        if stored_vulnerability is not None:
            return {
                "cve_id": stored_vulnerability.cve_id,
                "description": stored_vulnerability.description,
                "severity": stored_vulnerability.severity,
                "cvss_score": stored_vulnerability.cvss_score,
                "affected_software": stored_vulnerability.affected_software,
                "min_version": stored_vulnerability.min_version,
                "max_version": stored_vulnerability.max_version,
                "affected_products": [
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
                    for product in stored_vulnerability.affected_products
                ],
            }

    try:
        cve = get_cve(cve_id)
    except requests.exceptions.HTTPError as error:
        status_code = error.response.status_code if error.response is not None else None
        if status_code in (403, 429) or (status_code is not None and status_code >= 500):
            raise HTTPException(
                status_code=503,
                detail="NVD is temporarily unavailable.",
            ) from error
        raise HTTPException(
            status_code=502,
            detail="NVD returned an unsuccessful response.",
        ) from error
    except requests.exceptions.Timeout as error:
        raise HTTPException(
            status_code=503,
            detail="NVD request timed out.",
        ) from error
    except requests.exceptions.RequestException as error:
        raise HTTPException(
            status_code=503,
            detail="Unable to connect to NVD.",
        ) from error
    except (ValueError, TypeError) as error:
        raise HTTPException(
            status_code=502,
            detail="NVD returned an invalid response.",
        ) from error

    if cve is None:
        raise HTTPException(status_code=404, detail="CVE not found.")

    try:
        normalized = parse_cve(cve)
    except (ValueError, TypeError, KeyError) as error:
        raise HTTPException(
            status_code=502,
            detail="NVD returned CVE data that could not be parsed.",
        ) from error

    products = normalized["affected_products"]
    primary_product = products[0] if products else {}
    return {
        "cve_id": normalized["cve_id"],
        "description": normalized["description"],
        "severity": normalized["severity"],
        "cvss_score": normalized["cvss_score"],
        # Keep the requested single-entry convenience fields and expose all
        # CPE matches below so multi-product CVEs are not truncated.
        "affected_software": primary_product.get("affected_software"),
        "min_version": primary_product.get("min_version"),
        "max_version": primary_product.get("max_version"),
        "affected_products": products,
    }


@app.post("/nvd/assess", dependencies=[Depends(require_api_key)])
def assess_software_with_nvd(
    request: NvdAssessRequest,
    db: Session | None = Depends(get_db),
):
    if db is None:
        raise HTTPException(status_code=503, detail="Database is not configured.")
    try:
        return assess_stored_software(
            db,
            request.software_name,
            request.software_version,
        )
    except requests.exceptions.HTTPError as error:
        status_code = error.response.status_code if error.response is not None else None
        if status_code in (403, 429) or (status_code is not None and status_code >= 500):
            raise HTTPException(status_code=503, detail="NVD is temporarily unavailable.") from error
        raise HTTPException(status_code=502, detail="NVD returned an unsuccessful response.") from error
    except requests.exceptions.Timeout as error:
        raise HTTPException(status_code=503, detail="NVD request timed out.") from error
    except requests.exceptions.RequestException as error:
        raise HTTPException(status_code=503, detail="Unable to connect to NVD.") from error
    except (ValueError, TypeError, KeyError) as error:
        raise HTTPException(status_code=502, detail="NVD returned data that could not be parsed.") from error
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(status_code=503, detail="Unable to store NVD vulnerability data.") from error


@app.post("/nvd/sync", dependencies=[Depends(require_api_key)])
def sync_nvd(
    limit: int = Query(default=10, ge=1, le=2000),
    db: Session | None = Depends(get_db),
):
    """Ingest a small NVD page into the existing vulnerability tables."""
    if db is None:
        raise HTTPException(status_code=503, detail="Database is not configured.")
    try:
        return sync_nvd_cves(db, limit)
    except requests.exceptions.HTTPError as error:
        status_code = error.response.status_code if error.response is not None else None
        if status_code in (403, 429) or (status_code is not None and status_code >= 500):
            raise HTTPException(status_code=503, detail="NVD is temporarily unavailable.") from error
        raise HTTPException(status_code=502, detail="NVD returned an unsuccessful response.") from error
    except requests.exceptions.Timeout as error:
        raise HTTPException(status_code=503, detail="NVD request timed out.") from error
    except requests.exceptions.RequestException as error:
        raise HTTPException(status_code=503, detail="Unable to connect to NVD.") from error
    except ValueError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(status_code=503, detail="Unable to store NVD vulnerability data.") from error

@app.post("/match-vulnerability")
def match_vulnerability_endpoint(
    software_name: str,
    software_version: str,
    affected_software: str,
    min_version: str,
    max_version: str,
    min_version_inclusive: bool = True,
    max_version_inclusive: bool = True,
):
    result = match_vulnerability(
        software_name,
        software_version,
        affected_software,
        min_version,
        max_version,
        min_version_inclusive,
        max_version_inclusive,
    )

    return {
        "software": software_name,
        "version": software_version,
        "vulnerability_match": result
    }


def _match_cve_request(match_request: VulnerabilityMatchRequest) -> bool:
    vulnerability = match_request.vulnerability
    if vulnerability.affected_products:
        return match_affected_products(
            match_request.software_name,
            match_request.software_version,
            vulnerability.affected_products,
        )
    elif vulnerability.affected_software:
        return match_vulnerability(
            match_request.software_name,
            match_request.software_version,
            vulnerability.affected_software,
            vulnerability.min_version,
            vulnerability.max_version,
            vulnerability.min_version_inclusive,
            vulnerability.max_version_inclusive,
        )
    return False


@app.post("/match-cve")
def match_cve(match_request: VulnerabilityMatchRequest):
    vulnerability = match_request.vulnerability
    result = _match_cve_request(match_request)

    return {
        "cve_id": vulnerability.cve_id,
        "software": match_request.software_name,
        "installed_version": match_request.software_version,
        "vulnerability_match": result,
        "severity": vulnerability.severity,
        "cvss_score": vulnerability.cvss_score
    }


@app.post("/assess-risk")
def assess_cve_risk(match_request: VulnerabilityMatchRequest):
    vulnerability = match_request.vulnerability
    matched = _match_cve_request(match_request)
    return assess_risk(
        cve_id=vulnerability.cve_id,
        affected_software=match_request.software_name,
        installed_version=match_request.software_version,
        matched=matched,
        cvss_score=vulnerability.cvss_score,
        original_severity=vulnerability.severity,
    )
