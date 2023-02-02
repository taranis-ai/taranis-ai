from datetime import datetime, timedelta
from enum import Enum, auto
from functools import wraps
from flask import request
from flask_jwt_extended import (
    JWTManager,
    get_jwt,
    get_jwt_identity,
    verify_jwt_in_request,
)
from flask_jwt_extended.exceptions import JWTExtendedException

from core.managers import time_manager
from core.managers.log_manager import logger
from core.auth.keycloak_authenticator import KeycloakAuthenticator
from core.auth.openid_authenticator import OpenIDAuthenticator
from core.auth.test_authenticator import TestAuthenticator
from core.auth.database_authenticator import DatabaseAuthenticator
from core.model.collectors_node import CollectorsNode
from core.model.news_item import NewsItem
from core.model.osint_source import OSINTSourceGroup
from core.model.permission import Permission
from core.model.product_type import ProductType
from core.model.remote import RemoteAccess
from core.model.report_item import ReportItem
from core.model.token_blacklist import TokenBlacklist
from core.model.user import User
from core.config import Config

current_authenticator = TestAuthenticator()

api_key = Config.API_KEY


def cleanup_token_blacklist(app):
    with app.app_context():
        TokenBlacklist.delete_older(datetime.now() - timedelta(days=1))


def initialize(app):
    global current_authenticator

    JWTManager(app)

    authenticator = app.config.get("TARANIS_NG_AUTHENTICATOR", "test")
    if authenticator == "openid":
        current_authenticator = OpenIDAuthenticator()
    elif authenticator == "keycloak":
        current_authenticator = KeycloakAuthenticator()
    elif authenticator == "database":
        current_authenticator = DatabaseAuthenticator()
    else:
        current_authenticator = TestAuthenticator()

    with app.app_context():
        current_authenticator.initialize(app)

    time_manager.schedule_job_every_day("00:00", cleanup_token_blacklist, app)


def get_required_credentials():
    return current_authenticator.get_required_credentials()


def authenticate(credentials):
    logger.log_debug(f"credentials: {credentials}")
    return current_authenticator.authenticate(credentials)


def refresh(user):
    return current_authenticator.refresh(user)


def logout(token):
    return current_authenticator.logout(token)


class ACLCheck(Enum):
    OSINT_SOURCE_GROUP_ACCESS = auto()
    NEWS_ITEM_ACCESS = auto()
    NEWS_ITEM_MODIFY = auto()
    REPORT_ITEM_ACCESS = auto()
    REPORT_ITEM_MODIFY = auto()
    PRODUCT_TYPE_ACCESS = auto()
    PRODUCT_TYPE_MODIFY = auto()


def check_acl(item_id, acl_check, user):
    check_see = "SEE" in str(acl_check)
    check_access = "ACCESS" in str(acl_check)
    check_modify = "MODIFY" in str(acl_check)
    allowed = False
    item_type = "UNKNOWN"

    if acl_check == ACLCheck.OSINT_SOURCE_GROUP_ACCESS:
        item_type = "OSINT Source Group"
        allowed = OSINTSourceGroup.allowed_with_acl(item_id, user, check_see, check_access, check_modify)

    if acl_check in [ACLCheck.NEWS_ITEM_ACCESS, ACLCheck.NEWS_ITEM_MODIFY]:
        item_type = "News Item"
        allowed = NewsItem.allowed_with_acl(item_id, user, check_see, check_access, check_modify)

    if acl_check in [ACLCheck.REPORT_ITEM_ACCESS, ACLCheck.REPORT_ITEM_MODIFY]:
        item_type = "Report Item"
        allowed = ReportItem.allowed_with_acl(item_id, user, check_see, check_access, check_modify)

    if acl_check in [ACLCheck.PRODUCT_TYPE_ACCESS, ACLCheck.PRODUCT_TYPE_MODIFY]:
        item_type = "Product Type"
        allowed = ProductType.allowed_with_acl(item_id, user, check_see, check_access, check_modify)

    if not allowed:
        logger.log_debug(f"Unauthorized '{check_access or check_modify}' attempt to {item_type}: {item_id}")

    return allowed


def no_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        logger.store_activity("API_ACCESS", None)
        return fn(*args, **kwargs)

    return wrapper


def get_id_name_by_acl(acl):
    if "NEWS_ITEM" in acl.name:
        return "item_id"
    elif "REPORT_ITEM" in acl.name:
        return "report_item_id"
    elif "OSINT_SOURCE_GROUP" in acl.name:
        return "group_id"
    elif "PRODUCT" in acl.name:
        return "product_id"


def auth_required(permissions: list | str, acl=None):
    def auth_required_wrap(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            error = ({"error": "not authorized"}, 401)
            permissions_set = set(permissions) if isinstance(permissions, list) else {permissions}

            # do we have a JWT token?
            try:
                verify_jwt_in_request()
            except JWTExtendedException:
                logger.store_auth_error_activity("Missing JWT")
                return error

            # does it encode an identity?
            identity = get_jwt_identity()
            if not identity:
                logger.store_auth_error_activity(f"Missing identity in JWT: {get_jwt()}")
                return error

            user = User.find(identity)

            # does it include permissions?
            claims = get_jwt()
            user_claims = claims.get("user_claims")
            if not user_claims:
                logger.store_user_auth_error_activity(user, "", f"Missing permissions in JWT for identity: {identity}")
                return error

            permission_claims = set(user_claims.get("permissions"))

            # is there at least one match with the permissions required by the call?
            if not permissions_set.intersection(permission_claims):
                logger.store_user_auth_error_activity(
                    user,
                    "",
                    "Insufficient permissions in JWT for identity: {}".format(identity),
                )
                return error

            # if the object does have an ACL, do we match it?
            if acl and not check_acl(kwargs[get_id_name_by_acl(acl)], acl, user):
                logger.store_user_auth_error_activity(
                    user,
                    "",
                    "Access denied by ACL in JWT for identity: {}".format(identity),
                )
                return error

            return fn(*args, **kwargs)

        return wrapper

    return auth_required_wrap


def api_key_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        error = ({"error": "not authorized"}, 401)

        # do we have the authorization header?
        auth_header = request.headers.get("Authorization", None)
        if not auth_header:
            logger.store_auth_error_activity("Missing Authorization header")
            return error

        if not auth_header.startswith("Bearer"):
            logger.store_auth_error_activity("Missing Authorization Bearer")
            return error

        api_key = auth_header.replace("Bearer ", "")

        # does it match some of our collector's keys?
        if not CollectorsNode.exists_by_api_key(api_key) and Config.API_KEY != api_key:
            logger.store_auth_error_activity(f"Incorrect api key: {api_key}")
            return error

        # allow
        return fn(*args, **kwargs)

    return wrapper


def access_key_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        error = ({"error": "not authorized"}, 401)

        auth_header = request.headers.get("Authorization", None)
        if not auth_header:
            logger.store_auth_error_activity("Missing Authorization header for remote access")
            return error

        if not auth_header.startswith("Bearer"):
            logger.store_auth_error_activity("Missing Authorization Bearer for remote access")
            return error

        # does it match some of our remote peer's access keys?
        if not RemoteAccess.exists_by_access_key(auth_header.replace("Bearer ", "")):
            logger.store_auth_error_activity("Incorrect access key: " + auth_header.replace("Bearer ", "") + " for remote access")
            return error

        # allow
        return fn(*args, **kwargs)

    return wrapper


def get_access_key():
    return request.headers["Authorization"].replace("Bearer ", "")


def get_user_from_jwt() -> User | None:
    try:
        verify_jwt_in_request()
    except JWTExtendedException:
        return None
    identity = get_jwt_identity()

    return User.find(identity) if identity else None


def get_external_permissions_ids():
    return ["MY_ASSETS_ACCESS", "MY_ASSETS_CREATE", "MY_ASSETS_CONFIG"]


def get_external_permissions():
    return [Permission.find(permission_id) for permission_id in get_external_permissions_ids()]
