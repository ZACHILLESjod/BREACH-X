"""Bounded NVD ingestion for the existing vulnerability tables."""

from sqlalchemy.orm import Session

from app.repositories.vulnerability_repository import (
    list_vulnerability_ids,
    upsert_normalized_vulnerability,
)
from app.services.nvd_client import fetch_cves
from app.services.nvd_parser import parse_cve


def sync_nvd_cves(db: Session, limit: int = 10) -> dict[str, int]:
    """Fetch and persist a bounded NVD page, skipping duplicate CVE IDs."""
    raw_cves = fetch_cves(limit)
    existing_ids = list_vulnerability_ids(db)
    seen_ids = set(existing_ids)
    inserted = 0
    skipped_duplicates = 0
    failed = 0

    for raw_cve in raw_cves:
        cve_id = raw_cve.get("id") if isinstance(raw_cve, dict) else None
        normalized_id = cve_id.upper() if isinstance(cve_id, str) else None
        if not normalized_id or normalized_id in seen_ids:
            skipped_duplicates += 1
            continue

        try:
            normalized = parse_cve(raw_cve)
            upsert_normalized_vulnerability(db, normalized)
        except (ValueError, TypeError, KeyError):
            db.rollback()
            failed += 1
            continue

        seen_ids.add(normalized_id)
        inserted += 1

    return {
        "fetched": len(raw_cves),
        "inserted": inserted,
        "skipped_duplicates": skipped_duplicates,
        "failed": failed,
    }
