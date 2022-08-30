import uuid
from marshmallow import fields, post_load
from sqlalchemy import orm, func, or_, text

from core.managers.db_manager import db
from core.model.report_item import ReportItem
from core.model.user import User
from core.model.notification_template import NotificationTemplate
from shared.schema.asset import (
    AssetCpeSchema,
    AssetSchema,
    AssetPresentationSchema,
    AssetGroupSchema,
    AssetGroupPresentationSchema,
)
from shared.schema.user import UserIdSchema
from shared.schema.notification_template import NotificationTemplateIdSchema


class NewAssetCpeSchema(AssetCpeSchema):
    @post_load
    def make(self, data, **kwargs):
        return AssetCpe(**data)


class AssetCpe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.String())

    asset_id = db.Column(db.Integer, db.ForeignKey("asset.id"))
    asset = db.relationship("Asset")

    def __init__(self, value):
        self.id = None
        self.value = value


class NewAssetSchema(AssetSchema):
    asset_cpes = fields.Nested(NewAssetCpeSchema, many=True)

    @post_load
    def make(self, data, **kwargs):
        return Asset(**data)


class Asset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(), nullable=False)
    serial = db.Column(db.String())
    description = db.Column(db.String())

    asset_group_id = db.Column(db.String, db.ForeignKey("asset_group.id"))
    asset_group = db.relationship("AssetGroup")

    asset_cpes = db.relationship("AssetCpe", cascade="all, delete-orphan", back_populates="asset")

    vulnerabilities = db.relationship("AssetVulnerability", cascade="all, delete-orphan", back_populates="asset")
    vulnerabilities_count = db.Column(db.Integer, default=0)

    def __init__(self, id, name, serial, description, asset_group_id, asset_cpes):
        self.id = None
        self.name = name
        self.serial = serial
        self.description = description
        self.asset_group_id = asset_group_id
        self.asset_cpes = asset_cpes
        self.title = ""
        self.subtitle = ""
        self.tag = ""

    @orm.reconstructor
    def reconstruct(self):
        self.title = self.name
        self.subtitle = self.description
        self.tag = "mdi-laptop"

    @classmethod
    def get_by_cpe(cls, cpes):

        if len(cpes) > 0:
            query_string = "SELECT DISTINCT asset_id FROM asset_cpe WHERE value LIKE ANY(:cpes) OR {}"
            params = {"cpes": cpes}

            inner_query = ""
            for i in range(len(cpes)):
                if i > 0:
                    inner_query += " OR "
                param = "cpe" + str(i)
                inner_query += ":" + param + " LIKE value"
                params[param] = cpes[i]

            result = db.engine.execute(text(query_string.format(inner_query)), params)

            return [cls.query.get(row[0]) for row in result]
        else:
            return []

    @classmethod
    def remove_vulnerability(cls, report_item_id):
        vulnerabilities = AssetVulnerability.get_by_report(report_item_id)
        for vulnerability in vulnerabilities:
            vulnerability.asset.vulnerabilities_count -= 1
            db.session.delete(vulnerability)

    def add_vulnerability(self, report_item):
        for vulnerability in self.vulnerabilities:
            if vulnerability.report_item.id == report_item.id:
                return

        vulnerability = AssetVulnerability(self.id, report_item.id)
        db.session.add(vulnerability)
        self.vulnerabilities_count += 1

    def update_vulnerabilities(self):
        cpes = []
        for cpe in self.asset_cpes:
            cpes.append(cpe.value)

        report_item_ids = ReportItem.get_by_cpe(cpes)

        solved = []
        for vulnerability in self.vulnerabilities:
            if vulnerability.solved is True:
                solved.append(vulnerability.report_item_id)

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
    def solve_vulnerability(cls, user, group_id, asset_id, report_item_id, solved):
        asset = cls.query.get(asset_id)
        if AssetGroup.access_allowed(user, asset.asset_group_id):
            for vulnerability in asset.vulnerabilities:
                if vulnerability.report_item_id == report_item_id:
                    if solved is not vulnerability.solved:
                        if solved is True:
                            asset.vulnerabilities_count -= 1
                        else:
                            asset.vulnerabilities_count += 1
                    vulnerability.solved = solved
                    db.session.commit()
                    return

    @classmethod
    def get(cls, group_id, search, sort, vulnerable):
        query = cls.query.filter(Asset.asset_group_id == group_id)

        if vulnerable is not None:
            if vulnerable == "true":
                query = query.filter(Asset.vulnerabilities_count > 0)

        if search is not None:
            search_string = "%" + search.lower() + "%"
            query = query.join(AssetCpe, Asset.id == AssetCpe.asset_id).filter(
                or_(
                    func.lower(Asset.name).like(search_string),
                    func.lower(Asset.description).like(search_string),
                    func.lower(Asset.serial).like(search_string),
                    func.lower(AssetCpe.value).like(search_string),
                )
            )

        if sort is not None:
            if sort == "ALPHABETICAL":
                query = query.order_by(db.asc(Asset.name))
            else:
                query = query.order_by(db.desc(Asset.vulnerabilities_count))

        return query.all(), query.count()

    @classmethod
    def get_all_json(cls, user, group_id, search, sort, vulnerable):
        if AssetGroup.access_allowed(user, group_id):
            assets, count = cls.get(group_id, search, sort, vulnerable)
            asset_schema = AssetPresentationSchema(many=True)
            items = asset_schema.dump(assets)
            return {"total_count": count, "items": items}

    @classmethod
    def add(cls, user, group_id, data):
        schema = NewAssetSchema()
        asset = schema.load(data)
        asset.asset_group_id = group_id
        if AssetGroup.access_allowed(user, group_id):
            db.session.add(asset)
            asset.update_vulnerabilities()
            db.session.commit()

    @classmethod
    def update(cls, user, group_id, asset_id, data):
        asset = cls.query.get(asset_id)
        if AssetGroup.access_allowed(user, asset.asset_group_id):
            schema = NewAssetSchema()
            updated_asset = schema.load(data)
            asset.name = updated_asset.name
            asset.serial = updated_asset.serial
            asset.description = updated_asset.description
            asset.asset_cpes = updated_asset.asset_cpes
            asset.update_vulnerabilities()
            db.session.commit()

    @classmethod
    def delete(cls, user, group_id, id):
        asset = cls.query.get(id)
        if AssetGroup.access_allowed(user, asset.asset_group_id):
            db.session.delete(asset)
            db.session.commit()


class AssetVulnerability(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    solved = db.Column(db.Boolean, default=False)

    asset_id = db.Column(db.Integer, db.ForeignKey("asset.id"))
    asset = db.relationship("Asset", back_populates="vulnerabilities")

    report_item_id = db.Column(db.Integer, db.ForeignKey("report_item.id"))
    report_item = db.relationship("ReportItem")

    def __init__(self, asset_id, report_item_id):
        self.id = None
        self.asset_id = asset_id
        self.report_item_id = report_item_id

    @classmethod
    def get_by_report(cls, report_id):
        return cls.query.filter_by(report_item_id=report_id).all()


class NewAssetGroupGroupSchema(AssetGroupSchema):
    users = fields.Nested(UserIdSchema, many=True)
    templates = fields.Nested(NotificationTemplateIdSchema, many=True)

    @post_load
    def make(self, data, **kwargs):
        return AssetGroup(**data)


class AssetGroup(db.Model):
    id = db.Column(db.String(64), primary_key=True)
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())

    templates = db.relationship("NotificationTemplate", secondary="asset_group_notification_template")

    organizations = db.relationship("Organization", secondary="asset_group_organization")
    users = db.relationship("User", secondary="asset_group_user")

    def __init__(self, id, name, description, users, templates):
        self.id = str(uuid.uuid4())
        self.name = name
        self.description = description
        self.organizations = []
        self.users = []
        for user in users:
            self.users.append(User.find_by_id(user.id))

        self.templates = []
        for template in templates:
            self.templates.append(NotificationTemplate.find(template.id))

        self.title = ""
        self.subtitle = ""
        self.tag = ""

    @orm.reconstructor
    def reconstruct(self):
        self.title = self.name
        self.subtitle = self.description
        self.tag = "mdi-folder-multiple"

    @classmethod
    def find(cls, group_id):
        group = cls.query.get(group_id)
        return group

    @classmethod
    def access_allowed(cls, user, group_id):
        group = cls.query.get(group_id)
        return any(org in user.organizations for org in group.organizations)

    @classmethod
    def get(cls, search, organization):
        query = cls.query

        if organization is not None:
            query = query.join(
                AssetGroupOrganization,
                AssetGroup.id == AssetGroupOrganization.asset_group_id,
            )

        if search is not None:
            search_string = "%" + search.lower() + "%"
            query = query.filter(
                or_(
                    func.lower(AssetGroup.name).like(search_string),
                    func.lower(AssetGroup.description).like(search_string),
                )
            )

        return query.order_by(db.asc(AssetGroup.name)).all(), query.count()

    @classmethod
    def get_all_json(cls, user, search):
        groups, count = cls.get(search, user.organizations[0])
        permissions = user.get_permissions()
        if "MY_ASSETS_CONFIG" not in permissions:
            for group in groups[:]:
                if len(group.users) > 0:
                    found = False
                    for accessed_user in group.users:
                        if accessed_user.id == user.id:
                            found = True
                            break

                    if found is False:
                        groups.remove(group)
                        count -= 1

        group_schema = AssetGroupPresentationSchema(many=True)
        return {"total_count": count, "items": group_schema.dump(groups)}

    @classmethod
    def add(cls, user, data):
        new_group_schema = NewAssetGroupGroupSchema()
        group = new_group_schema.load(data)
        group.organizations = user.organizations
        for added_user in group.users[:]:
            if not any(org in added_user.organizations for org in group.organizations):
                group.users.remove(added_user)

        for added_template in group.templates[:]:
            if not any(org in added_template.organizations for org in group.organizations):
                group.temlates.remove(added_template)

        db.session.add(group)
        db.session.commit()

    @classmethod
    def delete(cls, user, group_id):
        group = cls.query.get(group_id)
        if any(org in user.organizations for org in group.organizations):
            db.session.delete(group)
            db.session.commit()

    @classmethod
    def update(cls, user, group_id, data):
        new_group_schema = NewAssetGroupGroupSchema()
        updated_group = new_group_schema.load(data)
        group = cls.query.get(group_id)
        if any(org in user.organizations for org in group.organizations):
            group.name = updated_group.name
            group.description = updated_group.description
            group.users = []
            for added_user in updated_group.users:
                if any(org in added_user.organizations for org in group.organizations):
                    group.users.append(added_user)

            group.templates = []
            for added_template in updated_group.templates:
                if any(org in added_template.organizations for org in group.organizations):
                    group.templates.append(added_template)

            db.session.commit()


class AssetGroupOrganization(db.Model):
    asset_group_id = db.Column(db.String, db.ForeignKey("asset_group.id"), primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey("organization.id"), primary_key=True)


class AssetGroupUser(db.Model):
    asset_group_id = db.Column(db.String, db.ForeignKey("asset_group.id"), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), primary_key=True)


class AssetGroupNotificationTemplate(db.Model):
    asset_group_id = db.Column(db.String, db.ForeignKey("asset_group.id"), primary_key=True)
    notification_template_id = db.Column(db.Integer, db.ForeignKey("notification_template.id"), primary_key=True)
