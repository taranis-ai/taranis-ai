import os
from datetime import datetime, timedelta
from enum import Enum, auto
from functools import wraps
import jwt
from flask import request
from flask_jwt_extended import JWTManager, get_jwt_claims, get_jwt_identity, verify_jwt_in_request, get_raw_jwt
from flask_jwt_extended.exceptions import JWTExtendedException

from managers import log_manager, time_manager
from auth.keycloak_authenticator import KeycloakAuthenticator
from auth.openid_authenticator import OpenIDAuthenticator
from auth.test_authenticator import TestAuthenticator
from model.collectors_node import CollectorsNode
from model.news_item import NewsItem
from model.osint_source import OSINTSourceGroup
from model.permission import Permission
from model.product_type import ProductType
from model.remote import RemoteAccess
from model.report_item import ReportItem
from model.token_blacklist import TokenBlacklist
from model.user import User

current_authenticator = None

api_key = os.getenv('API_KEY')


def cleanup_token_blacklist(app):
    with app.app_context():
        TokenBlacklist.delete_older(datetime.today() - timedelta(days=1))


def initialize(app):
    global current_authenticator

    JWTManager(app)

    which = os.getenv('TARANIS_NG_AUTHENTICATOR')
    if which == 'openid':
        current_authenticator = OpenIDAuthenticator()
    elif which == 'keycloak':
        current_authenticator = KeycloakAuthenticator()
    elif which == 'test':
        current_authenticator = TestAuthenticator()
    else:
        current_authenticator = TestAuthenticator()

    current_authenticator.initialize(app)

    time_manager.schedule_job_every_day("00:00", cleanup_token_blacklist, app)


def get_required_credentials():
    return current_authenticator.get_required_credentials()


def authenticate(credentials):
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
    check_see = 'SEE' in str(acl_check)
    check_access = 'ACCESS' in str(acl_check)
    check_modify = 'MODIFY' in str(acl_check)
    allowed = False
    item_type = 'UNKNOWN'

    if acl_check == ACLCheck.OSINT_SOURCE_GROUP_ACCESS:
        item_type = "OSINT Source Group"
        allowed = OSINTSourceGroup.allowed_with_acl(item_id, user, check_see, check_access, check_modify)

    if acl_check == ACLCheck.NEWS_ITEM_ACCESS or acl_check == ACLCheck.NEWS_ITEM_MODIFY:
        item_type = "News Item"
        allowed = NewsItem.allowed_with_acl(item_id, user, check_see, check_access, check_modify)

    if acl_check == ACLCheck.REPORT_ITEM_ACCESS or acl_check == ACLCheck.REPORT_ITEM_MODIFY:
        item_type = "Report Item"
        allowed = ReportItem.allowed_with_acl(item_id, user, check_see, check_access, check_modify)

    if acl_check == ACLCheck.PRODUCT_TYPE_ACCESS or acl_check == ACLCheck.PRODUCT_TYPE_MODIFY:
        item_type = "Product Type"
        allowed = ProductType.allowed_with_acl(item_id, user, check_see, check_access, check_modify)

    if not allowed:
        if check_access:
            log_manager.store_user_auth_error_activity(user,
                                                       "Unauthorized access attempt to " + item_type + ": " + item_id)
        else:
            log_manager.store_user_auth_error_activity(user,
                                                       "Unauthorized modification attempt to " + item_type
                                                       + ": " + item_id)

    return allowed


def no_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        log_manager.store_activity("API_ACCESS", None)
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


def auth_required(permissions, *acl_args):
    def auth_required_wrap(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            error = ({'error': 'not authorized'}, 401)

            if isinstance(permissions, list):
                permissions_set = set(permissions)
            else:
                permissions_set = {permissions}

            # do we have a JWT token?
            try:
                verify_jwt_in_request()
            except JWTExtendedException:
                log_manager.store_auth_error_activity("Missing JWT")
                return error

            # does it encode an identity?
            identity = get_jwt_identity()
            if not identity:
                log_manager.store_auth_error_activity("Missing identity in JWT: " + get_raw_jwt())
                return error

            user = User.find(identity)

            # does it include permissions?
            claims = get_jwt_claims()
            if not claims or 'permissions' not in claims:
                log_manager.store_user_auth_error_activity(user,
                                                           "Missing permissions in JWT for identity: " + identity)
                return error

            # is there at least one match with the permissions required by the call?
            if not permissions_set.intersection(set(claims['permissions'])):
                log_manager.store_user_auth_error_activity(user,
                                                           "Insufficient permissions in JWT for identity: " + identity)
                return error

            # if the object does have an ACL, do we match it?
            if len(acl_args) > 0:
                if not check_acl(kwargs[get_id_name_by_acl(acl_args[0])], acl_args[0], user):
                    log_manager.store_user_auth_error_activity(user,
                                                               "Access denied by ACL in JWT for identity: " + identity)
                    return error

            # allow
            log_manager.store_user_activity(user, str(permissions), str(request.json))
            return fn(*args, **kwargs)

        return wrapper

    return auth_required_wrap


def api_key_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        error = ({'error': 'not authorized'}, 401)

        # do we have the authorization header?
        if not request.headers.has_key('Authorization'):
            log_manager.store_auth_error_activity("Missing Authorization header for external access")
            return error

        # is it properly encoded?
        auth_header = request.headers['Authorization']
        if not auth_header.startswith('Bearer'):
            log_manager.store_auth_error_activity("Missing Authorization Bearer for external access")
            return error

        # does it match some of our collector's keys?
        if not CollectorsNode.exists_by_api_key(auth_header.replace('Bearer ', '')):
            log_manager.store_auth_error_activity("Incorrect api key: "
                                                  + auth_header.replace('Bearer ',
                                                                        '') + " for external access")
            return error

        # allow
        return fn(*args, **kwargs)

    return wrapper


def access_key_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        error = ({'error': 'not authorized'}, 401)

        # do we have the authorization header?
        if not request.headers.has_key('Authorization'):
            log_manager.store_auth_error_activity("Missing Authorization header for remote access")
            return error

        # is it properly encoded?
        auth_header = request.headers['Authorization']
        if not auth_header.startswith('Bearer'):
            log_manager.store_auth_error_activity("Missing Authorization Bearer for remote access")
            return error

        # does it match some of our remote peer's access keys?
        if not RemoteAccess.exists_by_access_key(auth_header.replace('Bearer ', '')):
            log_manager.store_auth_error_activity("Incorrect access key: "
                                                  + auth_header.replace('Bearer ',
                                                                        '') + " for remote access")
            return error

        # allow
        return fn(*args, **kwargs)

    return wrapper


def jwt_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):

        try:
            verify_jwt_in_request()
        except JWTExtendedException:
            log_manager.store_auth_error_activity("Missing JWT")
            return {'error': 'authorization required'}, 401

        identity = get_jwt_identity()
        if not identity:
            log_manager.store_auth_error_activity("Missing identity in JWT: " + get_raw_jwt())
            return {'error': 'authorization failed'}, 401

        user = User.find(identity)
        if user is None:
            log_manager.store_auth_error_activity("Unknown identity: " + identity)
            return {'error': 'authorization failed'}, 401

        log_manager.store_user_activity(user, "API_ACCESS", "Access permitted")
        return fn(*args, **kwargs)

    return wrapper


def get_access_key():
    return request.headers['Authorization'].replace('Bearer ', '')


def get_user_from_jwt():
    try:
        verify_jwt_in_request()
    except JWTExtendedException:
        return None

    identity = get_jwt_identity()
    if not identity:
        return None

    return User.find(identity)


def decode_user_from_jwt(jwt_token):
    decoded = jwt.decode(jwt_token, os.getenv('JWT_SECRET_KEY'))
    if decoded is not None:
        return User.find(decoded['sub'])


def get_external_permissions_ids():
    return ["MY_ASSETS_ACCESS", "MY_ASSETS_CREATE", "MY_ASSETS_CONFIG"]


def get_external_permissions():
    permissions = []
    for permission_id in get_external_permissions_ids():
        permissions.append(Permission.find(permission_id))

    return permissions
