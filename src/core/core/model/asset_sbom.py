"""An import starts as a private preview and becomes an asset's inventory on confirmation."""

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Mapped, deferred, relationship

from core.managers.db_manager import db
from core.model.base_model import UUID_STR_LENGTH, BaseModel


class AssetSbomImport(BaseModel):
    __tablename__ = "asset_sbom_import"

    id: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH), primary_key=True, default=BaseModel.uuid7_str)
    asset_id: Mapped[str | None] = db.Column(
        db.String(UUID_STR_LENGTH), db.ForeignKey("asset.id", ondelete="CASCADE"), nullable=True, unique=True
    )
    user_id: Mapped[str | None] = db.Column(db.String(UUID_STR_LENGTH), db.ForeignKey("user.id", ondelete="SET NULL"))
    organization_id: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH), db.ForeignKey("organization.id", ondelete="CASCADE"), nullable=False)
    filename: Mapped[str] = db.Column(db.String(255), nullable=False)
    sha256: Mapped[str] = db.Column(db.String(64), nullable=False, index=True)
    created: Mapped[datetime] = db.Column(db.DateTime, nullable=False, default=BaseModel.utcnow)
    confirmed: Mapped[datetime | None] = db.Column(db.DateTime)
    summary: Mapped[dict[str, Any]] = db.Column(db.JSON, nullable=False)
    components: Mapped[list["AssetSbomComponent"]] = relationship(cascade="all, delete-orphan", passive_deletes=True)
    findings: Mapped[list["AssetSbomFinding"]] = relationship(cascade="all, delete-orphan", passive_deletes=True)

    def __init__(self, filename: str, sha256: str, user_id: str, organization_id: str, summary: dict[str, Any]):
        self.filename = filename
        self.sha256 = sha256
        self.user_id = user_id
        self.organization_id = organization_id
        self.summary = summary


class AssetSbomComponent(BaseModel):
    __tablename__ = "asset_sbom_component"

    id: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH), primary_key=True, default=BaseModel.uuid7_str)
    import_id: Mapped[str] = db.Column(
        db.String(UUID_STR_LENGTH), db.ForeignKey("asset_sbom_import.id", ondelete="CASCADE"), nullable=False, index=True
    )
    position: Mapped[int] = db.Column(db.Integer, nullable=False)
    inventory: Mapped[dict[str, Any]] = db.Column(db.JSON, nullable=False)
    __table_args__ = (db.UniqueConstraint("import_id", "position"),)

    def __init__(self, position: int, inventory: dict[str, Any]):
        self.position = position
        self.inventory = inventory


class AssetSbomFindingComponent(BaseModel):
    """An exported finding can reference several installed package versions."""

    __tablename__ = "asset_sbom_finding_component"
    finding_id: Mapped[str] = db.Column(
        db.String(UUID_STR_LENGTH), db.ForeignKey("asset_sbom_finding.id", ondelete="CASCADE"), primary_key=True
    )
    component_id: Mapped[str] = db.Column(
        db.String(UUID_STR_LENGTH), db.ForeignKey("asset_sbom_component.id", ondelete="CASCADE"), primary_key=True, index=True
    )


class AssetSbomFinding(BaseModel):
    """Source-reported findings, independent of report associations and IOC enrichment."""

    __tablename__ = "asset_sbom_finding"
    id: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH), primary_key=True, default=BaseModel.uuid7_str)
    import_id: Mapped[str] = db.Column(
        db.String(UUID_STR_LENGTH), db.ForeignKey("asset_sbom_import.id", ondelete="CASCADE"), nullable=False, index=True
    )
    identifier: Mapped[str] = db.Column(db.String(255), nullable=False)
    cve_id: Mapped[str] = db.Column(db.String(255), nullable=False, default="", index=True)
    matching_enabled: Mapped[bool] = db.Column(db.Boolean, nullable=False, default=True)
    details: Mapped[dict[str, Any]] = db.Column(db.JSON, nullable=False)
    components: Mapped[list[AssetSbomComponent]] = relationship(secondary="asset_sbom_finding_component", passive_deletes=True)


class AssetSbomUpload(BaseModel):
    """Private job state; source bytes exist only until preparation finishes or fails."""

    __tablename__ = "asset_sbom_upload"

    id: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH), primary_key=True, default=BaseModel.uuid7_str)
    user_id: Mapped[str | None] = db.Column(db.String(UUID_STR_LENGTH), db.ForeignKey("user.id", ondelete="SET NULL"))
    organization_id: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH), db.ForeignKey("organization.id", ondelete="CASCADE"))
    target_asset_id: Mapped[str | None] = db.Column(db.String(UUID_STR_LENGTH))
    import_id: Mapped[str | None] = db.Column(db.String(UUID_STR_LENGTH), db.ForeignKey("asset_sbom_import.id", ondelete="SET NULL"))
    filename: Mapped[str] = db.Column(db.String(255), nullable=False)
    sha256: Mapped[str] = db.Column(db.String(64), nullable=False)
    source: Mapped[bytes | None] = deferred(db.Column(db.LargeBinary))
    status: Mapped[str] = db.Column(db.String(20), nullable=False, default="QUEUED")
    error: Mapped[str] = db.Column(db.Text, nullable=False, default="")
    components_received: Mapped[int] = db.Column(db.Integer, nullable=False, default=0)
    findings_received: Mapped[int] = db.Column(db.Integer, nullable=False, default=0)
    created: Mapped[datetime] = db.Column(db.DateTime, nullable=False, default=BaseModel.utcnow)
    updated: Mapped[datetime] = db.Column(db.DateTime, nullable=False, default=BaseModel.utcnow)

    def __init__(
        self,
        *,
        user_id: str,
        organization_id: str,
        target_asset_id: str | None,
        filename: str,
        sha256: str,
        source: bytes | None = None,
        status: str = "QUEUED",
        import_id: str | None = None,
    ):
        self.user_id = user_id
        self.organization_id = organization_id
        self.target_asset_id = target_asset_id
        self.filename = filename
        self.sha256 = sha256
        self.source = source
        self.status = status
        self.import_id = import_id


class AssetSbomUploadReference(BaseModel):
    """Temporary reference index for bounded worker finding batches."""

    __tablename__ = "asset_sbom_upload_reference"

    upload_id: Mapped[str] = db.Column(
        db.String(UUID_STR_LENGTH), db.ForeignKey("asset_sbom_upload.id", ondelete="CASCADE"), primary_key=True
    )
    reference_hash: Mapped[str] = db.Column(db.String(64), primary_key=True)
    component_id: Mapped[str] = db.Column(
        db.String(UUID_STR_LENGTH), db.ForeignKey("asset_sbom_component.id", ondelete="CASCADE"), nullable=False
    )
