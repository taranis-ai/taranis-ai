from dataclasses import dataclass
from sqlalchemy import cast, String, select
from sqlalchemy.orm import aliased
from sqlalchemy.sql import Select
from sqlalchemy.sql.expression import true

from core.managers.db_manager import db
from core.model.user import User
from core.model.role_based_access import RoleBasedAccess, RBACRole


@dataclass
class RBACQuery:
    user: User
    resource_type: str
    resource_id: str | None = None
    require_write_access: bool = False


class RoleBasedAccessService:
    @classmethod
    def user_has_access_to_resource(cls, rbac_query: RBACQuery) -> bool:
        """
        Check if a user has access to a resource based on RBACQuery parameters.
        """
        if not RoleBasedAccess.is_enabled_for_type(rbac_query.resource_type):
            return True
        return any(cls._is_authorized(acl_entry, rbac_query) for role in rbac_query.user.roles for acl_entry in role.acls)

    @staticmethod
    def _is_authorized(acl_entry: RoleBasedAccess, rbac_query: RBACQuery) -> bool:
        matches_resource = acl_entry.item_type.value == rbac_query.resource_type and acl_entry.item_id in [rbac_query.resource_id, "*"]
        is_enabled = acl_entry.enabled
        has_required_access = not rbac_query.require_write_access or not acl_entry.read_only

        return bool(matches_resource and is_enabled and has_required_access)

    @classmethod
    def filter_query_with_tlp(cls, query: Select, user: User) -> Select:
        from core.model.story import Story, StoryNewsItemAttribute
        from core.model.news_item_attribute import NewsItemAttribute

        user_tlp_level = user.get_highest_tlp()
        if user_tlp_level.value == "red":
            return query

        accessible_tlps = user_tlp_level.get_accessible_levels()

        TLPAttr = aliased(NewsItemAttribute)
        SNA = aliased(StoryNewsItemAttribute)

        query = (
            query.outerjoin(SNA, SNA.story_id == Story.id)
            .outerjoin(TLPAttr, db.and_(TLPAttr.id == SNA.news_item_attribute_id, TLPAttr.key == "TLP"))
            .filter(db.or_(TLPAttr.value.in_(accessible_tlps), TLPAttr.id.is_(None)))
        )

        return query

    @classmethod
    def filter_report_query_with_tlp(cls, query: Select, user: User) -> Select:
        from core.model.report_item import ReportItem, ReportItemAttribute, AttributeType

        user_tlp_level = user.get_highest_tlp()
        accessible_tlps = user_tlp_level.get_accessible_levels()

        TLPAttr = aliased(ReportItemAttribute)

        return query.outerjoin(TLPAttr, db.and_(TLPAttr.report_item_id == ReportItem.id, TLPAttr.attribute_type == AttributeType.TLP)).filter(
            db.or_(
                TLPAttr.value.in_(accessible_tlps),
                TLPAttr.id.is_(None),
            )
        )

    @classmethod
    def filter_query_with_acl(cls, query: Select, rbac_query: RBACQuery) -> Select:
        role_ids = [role.id for role in rbac_query.user.roles]
        item_type = rbac_query.resource_type
        if not RoleBasedAccess.is_enabled_for_type(item_type):
            return query
        model_class = cls.get_model_class(item_type)

        rbac_role_alias = aliased(RBACRole)
        role_based_access_alias = aliased(RoleBasedAccess)

        # Query to find item_ids accessible by any of the roles or check for wildcard access
        access_check_subquery = (
            select(role_based_access_alias.item_id)
            .join(rbac_role_alias, role_based_access_alias.id == rbac_role_alias.acl_id)
            .where(
                role_based_access_alias.item_type == item_type,
                role_based_access_alias.enabled == true(),
                rbac_role_alias.role_id.in_(role_ids),
            )
            .distinct()
        ).subquery()

        if db.session.execute(select(db.exists().where(access_check_subquery.c.item_id == "*"))).scalar():
            return query

        if item_type in ["report_item_type", "product_type", "word_list"]:
            id_field = cast(model_class.id, String)  # type: ignore
        else:
            id_field = model_class.id

        return query.where(id_field.in_(access_check_subquery))  # type: ignore

    @classmethod
    def get_model_class(cls, resource_type: str):
        """
        Get the SQLAlchemy model class for a given resource type.
        """

        from core.model.osint_source import OSINTSource, OSINTSourceGroup
        from core.model.word_list import WordList
        from core.model.report_item import ReportItemType
        from core.model.product_type import ProductType

        if resource_type == "osint_source":
            return OSINTSource

        if resource_type == "osint_source_group":
            return OSINTSourceGroup

        if resource_type == "word_list":
            return WordList

        if resource_type == "report_item_type":
            return ReportItemType

        if resource_type == "product_type":
            return ProductType

        raise ValueError(f"Unknown resource type: {resource_type}")
