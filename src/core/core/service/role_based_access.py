from dataclasses import dataclass
from sqlalchemy.orm.query import Query
from sqlalchemy.sql.expression import true, false

from core.model.user import User
from core.model.role_based_access import RoleBasedAccess
from core.model.osint_source import OSINTSource, OSINTSourceGroup
from core.model.word_list import WordList
from core.model.report_item import ReportItem, ReportItemType
from core.model.product_type import ProductType
from core.model.news_item import NewsItem
from core.model.product import Product


@dataclass
class RBACQuery:
    user: User
    resource_type: str
    resource_id: str | None = None
    require_write_access: bool = False


class RoleBasedAceessService:
    @classmethod
    def user_has_access_to_resource(cls, query: RBACQuery) -> bool:
        """
        Check if a user has access to a resource based on RBACQuery parameters.
        """
        return any(cls._is_authorized(acl_entry, query) for role in query.user.roles for acl_entry in role.acls)

    @classmethod
    def filter_query_with_acl(cls, query: Query, rbac_query: RBACQuery) -> Query:
        """
        Enhances an SQLAlchemy query based on role-based access control rules.

        :param query: The original SQLAlchemy query to be filtered based on ACL.
        :param rbac_query: An instance of RBACQuery containing user, resource type, and access requirements.
        :return: A modified query that reflects the access control rules.
        """
        user = rbac_query.user
        resource_type = rbac_query.resource_type
        require_write_access = rbac_query.require_write_access
        model_class = cls.get_model_class(resource_type)

        acl_subquery = (
            RoleBasedAccess.query.with_entities(RoleBasedAccess.item_id)
            .join(RoleBasedAccess.roles)
            .filter(
                RoleBasedAccess.item_type == resource_type, RoleBasedAccess.enabled == true(), RoleBasedAccess.roles.any(User.id == user.id)
            )
        )

        if require_write_access:
            acl_subquery = acl_subquery.filter(RoleBasedAccess.read_only == false())

        if model_class_id := model_class.id:
            query = query.filter(model_class_id.in_(acl_subquery.subquery()))

        return query

    @staticmethod
    def _is_authorized(acl_entry: RoleBasedAccess, query: RBACQuery) -> bool:
        matches_resource = acl_entry.item_type.value == query.resource_type and acl_entry.item_id == query.resource_id
        is_enabled = acl_entry.enabled
        has_required_access = not query.require_write_access or not acl_entry.read_only

        return bool(matches_resource and is_enabled and has_required_access)

    @classmethod
    def get_model_class(cls, resource_type: str):
        """
        Get the SQLAlchemy model class for a given resource type.
        """
        if resource_type == "osint_source":
            return OSINTSource
        elif resource_type == "osint_source_group":
            return OSINTSourceGroup
        elif resource_type == "word_list":
            return WordList
        elif resource_type == "report_item":
            return ReportItem
        elif resource_type == "report_item_type":
            return ReportItemType
        elif resource_type == "product_type":
            return ProductType
        elif resource_type == "product":
            return Product
        elif resource_type == "news_item":
            return NewsItem
        else:
            raise ValueError(f"Unknown resource type: {resource_type}")
