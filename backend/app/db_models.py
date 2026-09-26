from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AssetRecord(Base):
    __tablename__ = "assets"

    asset_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    hostname: Mapped[str] = mapped_column(String(255), nullable=False)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(100), nullable=False)
    operating_system: Mapped[str | None] = mapped_column(String(255), nullable=True)
    criticality: Mapped[str] = mapped_column(String(50), nullable=False, default="medium")

    software: Mapped[list["SoftwareRecord"]] = relationship(
        back_populates="asset",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class SoftwareRecord(Base):
    __tablename__ = "software"

    software_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(100), nullable=False)
    vendor: Mapped[str] = mapped_column(String(255), nullable=False)
    asset_id: Mapped[str] = mapped_column(
        ForeignKey("assets.asset_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    asset: Mapped["AssetRecord"] = relationship(back_populates="software")


class VulnerabilityRecord(Base):
    __tablename__ = "vulnerabilities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cve_id: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str | None] = mapped_column(String(20), nullable=True)
    cvss_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    affected_software: Mapped[str | None] = mapped_column(String(255), nullable=True)
    min_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    max_version: Mapped[str | None] = mapped_column(String(100), nullable=True)

    affected_products: Mapped[list["VulnerabilityAffectedProduct"]] = relationship(
        back_populates="vulnerability",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class VulnerabilityAffectedProduct(Base):
    __tablename__ = "vulnerability_affected_products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vulnerability_id: Mapped[int] = mapped_column(
        ForeignKey("vulnerabilities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    vendor: Mapped[str] = mapped_column(String(255), nullable=False)
    product: Mapped[str] = mapped_column(String(255), nullable=False)
    edition: Mapped[str | None] = mapped_column(String(255), nullable=True)
    affected_software: Mapped[str] = mapped_column(String(255), nullable=False)
    min_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    max_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    min_version_inclusive: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    max_version_inclusive: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    vulnerability: Mapped["VulnerabilityRecord"] = relationship(
        back_populates="affected_products"
    )
