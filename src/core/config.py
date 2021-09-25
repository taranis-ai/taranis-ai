import os
from dotenv import load_dotenv
load_dotenv()


class Config(object):
    REDIS_URL = os.getenv("REDIS_URL")

    DB_URL = os.getenv("DB_URL")
    DB_DATABASE = os.getenv("DB_DATABASE")
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")

    SQLALCHEMY_DATABASE_URI = 'postgresql+psycopg2://{user}:{pw}@{url}/{db}'.format(user=DB_USER, pw=DB_PASSWORD,
                                                                                    url=DB_URL, db=DB_DATABASE)
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    if "DB_POOL_SIZE" in os.environ:
        DB_POOL_SIZE = os.getenv("DB_POOL_SIZE")
        DB_POOL_RECYCLE = os.getenv("DB_POOL_RECYCLE")
        DB_POOL_TIMEOUT = os.getenv("DB_POOL_TIMEOUT")

        SQLALCHEMY_ENGINE_OPTIONS = {
            'pool_size': int(DB_POOL_SIZE),
            'pool_recycle': int(DB_POOL_RECYCLE),
            'pool_pre_ping': False,
            'pool_timeout': int(DB_POOL_TIMEOUT)
        }

    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
    JWT_IDENTITY_CLAIM = 'sub'
    JWT_ACCESS_TOKEN_EXPIRES = 14400
    DEBUG = True

    SECRET_KEY = 'OKdbmczZKFiteHVgKXiwFXZxKsLyRNvt'
    OIDC_CLIENT_SECRETS = 'client_secrets.json'
    OIDC_ID_TOKEN_COOKIE_SECURE = False
    OIDC_REQUIRE_VERIFIED_EMAIL = False
    OIDC_USER_INFO_ENABLED = True
    OIDC_OPENID_REALM = 'jiskb'
    OIDC_SCOPES = ['openid']
    OIDC_INTROSPECTION_AUTH_METHOD = 'client_secret_post'
    OIDC_TOKEN_TYPE_HINT = 'access_token'
    OIDC_RESOURCE_CHECK_AUD = True
    OIDC_CLOCK_SKEW = 560

    OPENID_LOGOUT_URL = os.getenv("OPENID_LOGOUT_URL")
