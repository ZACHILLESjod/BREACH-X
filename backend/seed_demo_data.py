"""Insert the BREACH-X dashboard's controlled, clearly labeled demo records.

The seed is additive: primary keys are checked before inserts, and existing
rows are never updated or removed. Demo vulnerabilities use synthetic IDs and
explicit descriptions so they cannot be mistaken for NVD records.

Run from ``backend`` with ``DATABASE_URL`` set:

    python seed_demo_data.py
"""

from __future__ import annotations

from sqlalchemy import inspect, select

from app.database import DATABASE_URL, SessionLocal, engine
from app.db_models import AssetRecord, SoftwareRecord, VulnerabilityRecord


DEMO_ASSETS = (
    {
        "asset_id": "breachx-demo-web-01",
        "hostname": "demo-web-01",
        "ip_address": "192.0.2.10",
        "asset_type": "server",
        "operating_system": "Ubuntu 22.04 LTS",
        "criticality": "high",
    },
    {
        "asset_id": "breachx-demo-app-01",
        "hostname": "demo-app-01",
        "ip_address": "192.0.2.20",
        "asset_type": "application server",
        "operating_system": "Debian 12",
        "criticality": "medium",
    },
    {
        "asset_id": "breachx-demo-workstation-01",
        "hostname": "demo-workstation-01",
        "ip_address": "192.0.2.30",
        "asset_type": "workstation",
        "operating_system": "Windows 11",
        "criticality": "low",
    },
)

DEMO_SOFTWARE = (
    {"software_id": "breachx-demo-sw-web-apache", "name": "Apache HTTP Server", "version": "2.4.49", "vendor": "Apache", "asset_id": "breachx-demo-web-01"},
    {"software_id": "breachx-demo-sw-web-openssl", "name": "OpenSSL", "version": "3.0.5", "vendor": "OpenSSL", "asset_id": "breachx-demo-web-01"},
    {"software_id": "breachx-demo-sw-app-apache", "name": "Apache HTTP Server", "version": "2.4.50", "vendor": "Apache", "asset_id": "breachx-demo-app-01"},
    {"software_id": "breachx-demo-sw-app-openssl", "name": "OpenSSL", "version": "3.0.8", "vendor": "OpenSSL", "asset_id": "breachx-demo-app-01"},
    {"software_id": "breachx-demo-sw-ws-firefox", "name": "Firefox", "version": "131.0", "vendor": "Mozilla", "asset_id": "breachx-demo-workstation-01"},
    {"software_id": "breachx-demo-sw-ws-thunderbird", "name": "Thunderbird", "version": "128.3.0", "vendor": "Mozilla", "asset_id": "breachx-demo-workstation-01"},
)

DEMO_VULNERABILITIES = (
    {
        "cve_id": "BREACHX-DEMO-CRITICAL-001",
        "description": "BREACH-X demo-only Firefox version-range finding; not an NVD record.",
        "severity": "CRITICAL",
        "cvss_score": 9.8,
        "affected_software": "Firefox",
        "min_version": "0",
        "max_version": "131.99.99",
    },
    {
        "cve_id": "BREACHX-DEMO-HIGH-001",
        "description": "BREACH-X demo-only Apache HTTP Server version-range finding; not an NVD record.",
        "severity": "HIGH",
        "cvss_score": 8.1,
        "affected_software": "Apache HTTP Server",
        "min_version": "2.4.0",
        "max_version": "2.4.49",
    },
    {
        "cve_id": "BREACHX-DEMO-MEDIUM-001",
        "description": "BREACH-X demo-only OpenSSL version-range finding; not an NVD record.",
        "severity": "MEDIUM",
        "cvss_score": 6.5,
        "affected_software": "OpenSSL",
        "min_version": "3.0.0",
        "max_version": "3.0.7",
    },
    {
        "cve_id": "BREACHX-DEMO-LOW-001",
        "description": "BREACH-X demo-only Thunderbird version-range finding; not an NVD record.",
        "severity": "LOW",
        "cvss_score": 3.7,
        "affected_software": "Thunderbird",
        "min_version": "128.0",
        "max_version": "128.3.99",
    },
)


def seed_demo_data() -> dict[str, int]:
    if not DATABASE_URL or engine is None:
        raise RuntimeError("DATABASE_URL is not configured in this process.")

    required_tables = {"assets", "software", "vulnerabilities"}
    present_tables = set(inspect(engine).get_table_names())
    missing_tables = required_tables - present_tables
    if missing_tables:
        raise RuntimeError(
            "Required tables are missing; run the normal table setup first: "
            + ", ".join(sorted(missing_tables))
        )

    created = {"assets": 0, "software": 0, "vulnerabilities": 0}
    with SessionLocal() as db:
        try:
            # Insert assets first so every software row has a valid parent.
            for values in DEMO_ASSETS:
                if db.get(AssetRecord, values["asset_id"]) is None:
                    db.add(AssetRecord(**values))
                    created["assets"] += 1
            db.flush()

            for values in DEMO_SOFTWARE:
                if db.get(SoftwareRecord, values["software_id"]) is None:
                    db.add(SoftwareRecord(**values))
                    created["software"] += 1
            db.flush()

            for values in DEMO_VULNERABILITIES:
                existing = db.scalar(
                    select(VulnerabilityRecord.id)
                    .where(VulnerabilityRecord.cve_id == values["cve_id"])
                    .limit(1)
                )
                if existing is None:
                    db.add(VulnerabilityRecord(**values))
                    created["vulnerabilities"] += 1

            db.commit()
        except Exception:
            db.rollback()
            raise

    return created


if __name__ == "__main__":
    if engine is None:
        raise SystemExit("DATABASE_URL is not configured in this process.")
    with engine.connect() as connection:
        database_name = connection.exec_driver_sql(
            "SELECT current_database()"
        ).scalar_one()
    result = seed_demo_data()
    print(f"Seeded database: {database_name}")
    print(
        "Inserted records: "
        f"assets={result['assets']}, "
        f"software={result['software']}, "
        f"vulnerabilities={result['vulnerabilities']}"
    )
    print("Existing rows were left unchanged; rerun to verify idempotency.")
