from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db_models import AssetRecord, SoftwareRecord
from app.models.asset import Asset
from app.models.software import Software


def save_asset(db: Session, asset: Asset) -> AssetRecord:
    record = db.get(AssetRecord, asset.asset_id)
    if record is None:
        record = AssetRecord(asset_id=asset.asset_id)
        db.add(record)

    record.hostname = asset.hostname
    record.ip_address = asset.ip_address
    record.asset_type = asset.asset_type
    record.operating_system = asset.operating_system
    record.criticality = asset.criticality
    db.commit()
    db.refresh(record)
    return record


def save_software(db: Session, software: Software) -> SoftwareRecord | None:
    if db.get(AssetRecord, software.asset_id) is None:
        return None

    record = db.get(SoftwareRecord, software.software_id)
    if record is None:
        record = SoftwareRecord(software_id=software.software_id)
        db.add(record)

    record.name = software.name
    record.version = software.version
    record.vendor = software.vendor
    record.asset_id = software.asset_id
    db.commit()
    db.refresh(record)
    return record


def get_asset_with_software(db: Session, asset_id: str) -> AssetRecord | None:
    statement = (
        select(AssetRecord)
        .options(selectinload(AssetRecord.software))
        .where(AssetRecord.asset_id == asset_id)
    )
    return db.scalar(statement)


def list_assets(db: Session) -> list[AssetRecord]:
    statement = select(AssetRecord).order_by(AssetRecord.asset_id)
    return list(db.scalars(statement).all())
