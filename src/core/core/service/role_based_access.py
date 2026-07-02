from dataclasses import dataclass

from sqlalchemy import String, cast, select
from sqlalchemy.orm import aliased
from sqlalchemy.sql import Select
from sqlalchemy.sql.expression import true

from core.managers.db_manager import db
from core.model.role_based_access import ItemType, RBACRole, RoleBasedAccess
from core.model.user import User


@dataclass
class RBACQuery:
    user: User
    resource_type: str | ItemType
    resource_id: str | None = None
    require_write_access: bool = False


class RoleBasedAccessService:
    @classmethod
    def user_has_access_to_resource(cls, rbac_query: RBACQuery) -> bool:
        """
        Check if a user has access to a resource based on RBACQuery parameters.
        """
        if cls._user_bypasses_acl(rbac_query.user):
            return True

        resource_type = cls._item_type(rbac_query.resource_type)
        if not cls._is_enabled_for_resource_type(resource_type):
            return True
        return any(cls._is_authorized(acl_entry, rbac_query) for role in rbac_query.user.roles for acl_entry in role.acls)

    @classmethod
    def _is_authorized(cls, acl_entry: RoleBasedAccess, rbac_query: RBACQuery) -> bool:
        if not acl_entry.enabled:
            return False
        if rbac_query.require_write_access and acl_entry.read_only:
            return False

        resource_type = cls._item_type(rbac_query.resource_type)
        acl_item_type = cls._item_type(acl_entry.item_type)

        if acl_item_type == resource_type:
            return acl_entry.item_id in [rbac_query.resource_id, "*"]

        if resource_type == ItemType.OSINT_SOURCE and acl_item_type == ItemType.OSINT_SOURCE_GROUP:
            return acl_entry.item_id == "*" or cls._source_is_in_group(rbac_query.resource_id, acl_entry.item_id)

        return False

    @staticmethod
    def _user_bypasses_acl(user: User) -> bool:
        try:
            return "ADMIN_OPERATIONS" in (user.get_permissions() or [])
        except (AttributeError, TypeError):
            return False

    @staticmethod
    def _item_type(item_type: str | ItemType) -> ItemType:
        return item_type if isinstance(item_type, ItemType) else ItemType(item_type)

    @classmethod
    def _is_enabled_for_resource_type(cls, resource_type: ItemType) -> bool:
        if resource_type == ItemType.OSINT_SOURCE:
            return RoleBasedAccess.is_enabled_for_type(ItemType.OSINT_SOURCE) or RoleBasedAccess.is_enabled_for_type(
                ItemType.OSINT_SOURCE_GROUP
            )
        return RoleBasedAccess.is_enabled_for_type(resource_type)

    @staticmethod
    def _source_is_in_group(source_id: str | None, group_id: str | None) -> bool:
        if not source_id or not group_id:
            return False

        from core.model.osint_source import OSINTSource, OSINTSourceGroup, OSINTSourceGroupOSINTSource

        source = OSINTSource.get(source_id)
        group = OSINTSourceGroup.get(group_id)
        if not source or not group:
            return False

        query = select(
            db.exists().where(
                OSINTSourceGroupOSINTSource.osint_source_id == source.id,
                OSINTSourceGroupOSINTSource.osint_source_group_id == group.id,
            )
        )
        return bool(db.session.execute(query).scalar())

    @classmethod
    def filter_query_with_tlp(cls, query: Select, user: User) -> Select:
        from core.model.news_item_attribute import NewsItemAttribute
        from core.model.story import Story, StoryNewsItemAttribute

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
        from core.model.report_item import AttributeType, ReportItem, ReportItemAttribute

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
        item_type = cls._item_type(rbac_query.resource_type)
        if cls._user_bypasses_acl(rbac_query.user) or not cls._is_enabled_for_resource_type(item_type):
            return query

        if item_type == ItemType.OSINT_SOURCE:
            return cls._filter_osint_source_query_with_acl(query, role_ids, rbac_query.require_write_access)

        model_class = cls.get_model_class(item_type)
        access_check_query = cls._acl_item_ids_query(item_type, role_ids, rbac_query.require_write_access)

        if cls._has_wildcard_access(access_check_query):
            return query

        if item_type in {ItemType.REPORT_ITEM_TYPE, ItemType.PRODUCT_TYPE, ItemType.WORD_LIST}:
            id_field = cast(model_class.id, String)  # type: ignore
        else:
            id_field = model_class.id

        return query.where(id_field.in_(access_check_query))  # type: ignore

    @classmethod
    def _filter_osint_source_query_with_acl(cls, query: Select, role_ids: list[str], require_write_access: bool) -> Select:
        from core.model.osint_source import OSINTSource, OSINTSourceGroupOSINTSource

        source_access_query = cls._acl_item_ids_query(ItemType.OSINT_SOURCE, role_ids, require_write_access)
        group_access_query = cls._acl_item_ids_query(ItemType.OSINT_SOURCE_GROUP, role_ids, require_write_access)

        if cls._has_wildcard_access(source_access_query) or cls._has_wildcard_access(group_access_query):
            return query

        inherited_source_ids = (
            select(OSINTSourceGroupOSINTSource.osint_source_id)
            .where(OSINTSourceGroupOSINTSource.osint_source_group_id.in_(group_access_query))
            .distinct()
        )

        return query.where(db.or_(OSINTSource.id.in_(source_access_query), OSINTSource.id.in_(inherited_source_ids)))

    @staticmethod
    def _acl_item_ids_query(item_type: ItemType, role_ids: list[str], require_write_access: bool) -> Select:
        rbac_role_alias = aliased(RBACRole)
        role_based_access_alias = aliased(RoleBasedAccess)

        query = (
            select(role_based_access_alias.item_id)
            .join(rbac_role_alias, role_based_access_alias.id == rbac_role_alias.acl_id)
            .where(
                role_based_access_alias.item_type == item_type,
                role_based_access_alias.enabled == true(),
                rbac_role_alias.role_id.in_(role_ids),
            )
            .distinct()
        )
        if require_write_access:
            query = query.where(role_based_access_alias.read_only.is_(False))
        return query

    @staticmethod
    def _has_wildcard_access(access_query: Select) -> bool:
        access_subquery = access_query.subquery()
        return bool(db.session.execute(select(db.exists().where(access_subquery.c.item_id == "*"))).scalar())

    @classmethod
    def get_model_class(cls, resource_type: str):
        """
        Get the SQLAlchemy model class for a given resource type.
        """

        from core.model.osint_source import OSINTSource, OSINTSourceGroup
        from core.model.product_type import ProductType
        from core.model.report_item import ReportItemType
        from core.model.word_list import WordList

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
