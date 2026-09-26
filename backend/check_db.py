import os
from sqlalchemy import create_engine, text

u = os.getenv("DATABASE_URL")

print("DATABASE_URL configured:", bool(u))

if not u:
    raise SystemExit("DATABASE_URL is not configured.")

engine = create_engine(u)

with engine.connect() as c:
    print("DB:", c.execute(text("""
        SELECT current_database(), current_schema(),
               inet_server_addr(), inet_server_port()
    """)).fetchone())

    rows = c.execute(text("""
        SELECT id, cve_id, description,
               affected_software, min_version, max_version
        FROM vulnerabilities
        WHERE upper(trim(cve_id)) = :cve
    """), {"cve": "CVE-2024-12345"}).fetchall()

    print("CVE ROW:", rows)
