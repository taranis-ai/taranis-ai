"""An import starts as a private preview and becomes an asset's inventory on confirmation."""

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Mapped, relationship

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
