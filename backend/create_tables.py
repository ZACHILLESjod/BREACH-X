from sqlalchemy import text

from app.database import Base, DATABASE_URL, engine
import app.db_models  # Registers ORM models with Base metadata.


def migrate_vulnerability_columns() -> None:
    if engine is None or engine.dialect.name != "postgresql":
        return
    columns = ("description", "severity", "cvss_score", "affected_software", "min_version", "max_version")
    with engine.begin() as connection:
        for column in columns:
            connection.execute(text(f"ALTER TABLE vulnerabilities ALTER COLUMN {column} DROP NOT NULL"))


def main() -> None:
    if not DATABASE_URL or engine is None:
        print("DATABASE_URL is not configured; no tables were created.")
        return

    Base.metadata.create_all(bind=engine)
    migrate_vulnerability_columns()
    print("Database tables created.")


if __name__ == "__main__":
    main()
