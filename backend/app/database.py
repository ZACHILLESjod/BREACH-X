import os

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import declarative_base, sessionmaker


DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    database_url = make_url(DATABASE_URL)
    if database_url.drivername in {"postgres", "postgresql"}:
        database_url = database_url.set(drivername="postgresql+psycopg")
    DATABASE_URL = database_url.render_as_string(hide_password=False)

engine = (
    create_engine(DATABASE_URL, pool_pre_ping=True)
    if DATABASE_URL
    else None
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    if engine is None:
        yield None
        return

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
