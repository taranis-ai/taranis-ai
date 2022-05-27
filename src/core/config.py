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
            'pool_pre_ping': True,
            'pool_timeout': int(DB_POOL_TIMEOUT)
        }

    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
    JWT_IDENTITY_CLAIM = 'sub'
    JWT_ACCESS_TOKEN_EXPIRES = 14400
    DEBUG = os.getenv('DEBUG').lower() == 'true'

    SECRET_KEY = 'OKdbmczZKFiteHVgKXiwFXZxKsLyRNvt'

    OPENID_CLIENT_ID = os.getenv('OPENID_CLIENT_ID')
    OPENID_CLIENT_SECRET = os.getenv('OPENID_CLIENT_SECRET')
    OPENID_METADAT_URL = 'http://keycloak/realms/master/.well-known/openid-configuration'

