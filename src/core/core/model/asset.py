import uuid
from sqlalchemy import or_
from sqlalchemy.sql import Select
from sqlalchemy.orm import Mapped, relationship
from typing import Any

from core.managers.db_manager import db
from core.model.base_model import BaseModel
from core.model.report_item import ReportItem
from core.model.organization import Organization


class Asset(BaseModel):
    __tablename__ = "asset"

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    name: Mapped[str] = db.Column(db.String(), nullable=False)
    serial: Mapped[str] = db.Column(db.String())
    description: Mapped[str] = db.Column(db.String())

    asset_group_id: Mapped[str] = db.Column(db.String, db.ForeignKey("asset_group.id"))
    asset_group: Mapped["AssetGroup"] = relationship("AssetGroup")

    asset_cpes: Mapped[list["AssetCpe"]] = relationship("AssetCpe", cascade="all, delete-orphan", back_populates="asset")

    vulnerabilities: Mapped[list["AssetVulnerability"]] = relationship(
        "AssetVulnerability", cascade="all, delete-orphan", back_populates="asset"
    )
    vulnerabilities_count: Mapped[int] = db.Column(db.Integer, default=0)

    def __init__(self, name, serial, description, group, asset_cpes=None, id=None):
        if id:
            self.id = id
        self.name = name
        self.serial = serial
        self.description = description
        self.asset_group_id = group if isinstance(group, str) else group.id
        self.asset_cpes = [a for a in (AssetCpe.get(cpe) for cpe in asset_cpes) if a] if asset_cpes else []

    @classmethod
    def get_by_cpe(cls, cpes):
        if len(cpes) <= 0:
            return []

        return cls.get_filtered(
            db.select(cls).join(AssetCpe, cls.id == AssetCpe.asset_id).filter(db.or_(*[AssetCpe.value.like(cpe) for cpe in cpes])).distinct()
        )

    @classmethod
    def remove_vulnerability(cls, report_item_id):
        vulnerabilities = AssetVulnerability.get_by_report(report_item_id)
        if not vulnerabilities:
            return
        for vulnerability in vulnerabilities:
            vulnerability.asset.vulnerabilities_count -= 1  # type: ignore
            db.session.delete(vulnerability)

    def add_vulnerability(self, report_item):
        for vulnerability in self.vulnerabilities:
            if vulnerability.report_item.id == report_item.id:
                return

        vulnerability = AssetVulnerability(self.id, report_item.id)
        db.session.add(vulnerability)
        self.vulnerabilities_count += 1

    def update_vulnerabilities(self):
        cpes = [cpe.value for cpe in self.asset_cpes if cpe]
        report_item_ids = ReportItem.get_by_cpe(cpes)
        if not report_item_ids:
            return

        solved = [vulnerability.report_item_id for vulnerability in self.vulnerabilities if vulnerability.solved is True]
        self.vulnerabilities = []
        self.vulnerabilities_count = 0
        for report_item_id in report_item_ids:
            vulnerability = AssetVulnerability(self.id, report_item_id)
            if report_item_id in solved:
                vulnerability.solved = True
            else:
                self.vulnerabilities_count += 1
            self.vulnerabilities.append(vulnerability)

    @classmethod
    def solve_vulnerability(cls, organization: Organization, asset_id, report_item_id, solved):
        asset = cls.get(asset_id)
        if not asset:
            return {"error": "Asset Not Found"}, 404
        if not AssetGroup.access_allowed(organization, asset.asset_group_id):
            return {"error": "Access Denied"}, 403

        for vulnerability in asset.vulnerabilities:
            if vulnerability.report_item_id == report_item_id:
                if solved is not vulnerability.solved:
                    if solved:
                        asset.vulnerabilities_count -= 1
                    else:
                        asset.vulnerabilities_count += 1
                vulnerability.solved = solved
                db.session.commit()
                return

    @classmethod
    def get_filter_query(cls, filter_args: dict) -> Select:
        query = db.select(cls)

        if search := filter_args.get("search"):
            query = query.join(AssetCpe, Asset.id == AssetCpe.asset_id).filter(
                or_(
                    Asset.name.ilike(f"%{search}%"),
                    Asset.description.ilike(f"%{search}%"),
                    Asset.serial.ilike(f"%{search}%"),
                    AssetCpe.value.ilike(f"%{search}%"),
                )
            )

        if group_id := filter_args.get("group"):
            query = query.filter(Asset.asset_group_id == group_id)

        if vulnerable := filter_args.get("vulnerable"):
            if vulnerable == "true":
                query = query.filter(Asset.vulnerabilities_count > 0)
            else:
                query = query.filter(Asset.vulnerabilities_count == 0)

        if organization := filter_args.get("organization"):
            query = query.join(AssetGroup, Asset.asset_group_id == AssetGroup.id).filter(AssetGroup.organization == organization)

        if sort := filter_args.get("sort"):
            if sort == "ALPHABETICAL":
                query = query.order_by(db.asc(Asset.name))
            else:
                query = query.order_by(db.desc(Asset.vulnerabilities_count))

        return query

    def to_dict(self):
        data = super().to_dict()
        data["asset_cpes"] = [asset_cpe.id for asset_cpe in self.asset_cpes if asset_cpe]
        data["vulnerabilities"] = [vulnerability.id for vulnerability in self.vulnerabilities]
        return data

    @classmethod
    def get_for_api(cls, item_id, organization: Organization) -> tuple[dict[str, Any], int]:
        if item := cls.get(item_id):
            if AssetGroup.access_allowed(organization, item.asset_group_id):
                return item.to_dict(), 200
        return {"error": f"{cls.__name__} {item_id} not found"}, 404

    @classmethod
    def add(cls, organization: Organization, data) -> tuple[dict, int]:
        asset = cls.from_dict(data)
        if not AssetGroup.access_allowed(organization, asset.asset_group_id):
            return {"error": "Access Denied"}, 403

        db.session.add(asset)
        asset.update_vulnerabilities()
        db.session.commit()
        return {"message": "Asset added", "id": asset.id}, 201

    @classmethod
    def update(cls, organization: Organization, asset_id, data) -> tuple[dict, int]:
        asset = cls.get(asset_id)
        if not asset:
            return {"error": "Asset Not Found"}, 404

        if not AssetGroup.access_allowed(organization, asset.asset_group_id):
            return {"error": "Access Denied"}, 403
        for key, value in data.items():
            if hasattr(asset, key) and key != "id":
                setattr(asset, key, value)
        asset.update_vulnerabilities()
        db.session.commit()
        return {"message": "Asset updated", "id": asset.id}, 201

    @classmethod
    def delete(cls, organization: Organization, id) -> tuple[dict, int]:
        asset = cls.get(id)
        if not asset:
            return {"error": "Asset Not Found"}, 404

        if not AssetGroup.access_allowed(organization, asset.asset_group_id):
            return {"error": "Access Denied"}, 403

        db.session.delete(asset)
        db.session.commit()
        return {"message": "Asset deleted", "id": asset.id}, 200


class AssetVulnerability(BaseModel):
    __tablename__ = "asset_vulnerability"

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    solved: Mapped[bool] = db.Column(db.Boolean, default=False)

    asset_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey("asset.id"))
    asset: Mapped["Asset"] = relationship("Asset", back_populates="vulnerabilities")

    report_item_id: Mapped[str] = db.Column(db.String(64), db.ForeignKey("report_item.id"))
    report_item: Mapped["ReportItem"] = relationship("ReportItem")

    def __init__(self, asset_id, report_item_id):
        self.asset_id = asset_id
        self.report_item_id = report_item_id

    @classmethod
    def get_by_report(cls, report_id):
        return cls.get_filtered(db.select(cls).filter_by(report_item_id=report_id))


class AssetGroup(BaseModel):
    __tablename__ = "asset_group"

    id: Mapped[str] = db.Column(db.String(64), primary_key=True)
    name: Mapped[str] = db.Column(db.String(), nullable=False)
    description: Mapped[str] = db.Column(db.String())

    organization_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey("organization.id"))
    organization: Mapped["Organization|None"] = relationship("Organization")

    def __init__(self, name, description, organization, id=None):
        self.id = id or str(uuid.uuid4())
        self.name = name
        self.description = description
        self.organization = Organization.get(organization) if isinstance(organization, int) else organization

    @classmethod
    def access_allowed(cls, organization: Organization, group_id: str) -> bool:
        if group_id == "default":
            return True
        if group := cls.get(group_id):
            return group.organization == organization
        return False

    @classmethod
    def get_default_group(cls):
        return cls.get("default")

    @classmethod
    def get_for_api(cls, item_id, organization: Organization) -> tuple[dict[str, Any], int]:
        if not cls.access_allowed(organization, item_id):
            return {"error": "Access denied"}, 403

        return super().get_for_api(item_id)

    @classmethod
    def get_filter_query(cls, filter_args: dict) -> Select:
        query = db.select(cls)

        if search := filter_args.get("search"):
            query = query.filter(
                or_(
                    AssetGroup.name.ilike(f"%{search}%"),
                    AssetGroup.description.ilike(f"%{search}%"),
                )
            )

        if organization := filter_args.get("organization"):
            query = query.filter_by(organization_id=organization.id)

        return query.order_by(db.asc(AssetGroup.name))

    @classmethod
    def delete(cls, organization: Organization, group_id):
        if group_id == "default":
            return {"error": "Cannot delete default group"}, 400
        if not cls.access_allowed(organization, group_id):
            return {"error": "Access denied"}, 403

        group = cls.get(group_id)
        db.session.delete(group)
        db.session.commit()

        return {"message": "Group deleted"}, 200

    @classmethod
    def update(cls, organization: Organization, group_id, data):
        if not cls.access_allowed(organization, group_id):
            return {"error": "Access denied"}, 403

        group = cls.get(group_id)
        if not group:
            return {"error": "Group not found"}, 404

        if name := data.get("name"):
            group.name = name
        if description := data.get("description"):
            group.description = description
        db.session.commit()
        return {"message": "Group updated"}, 200


class AssetCpe(BaseModel):
    __tablename__ = "asset_cpe"

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    value: Mapped[str] = db.Column(db.String())

    asset_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey("asset.id"))
    asset: Mapped["Asset"] = relationship("Asset")

    def __init__(self, value):
        self.value = value
