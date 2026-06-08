import sentry_sdk

from core.config import Config


def initialize():
    if not Config.TARANIS_SENTRY_DSN:
        return

    sentry_sdk.init(
        dsn=Config.TARANIS_SENTRY_DSN,
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
        enable_logs=True,
        send_default_pii=True,
        enable_db_query_source=True,
    )
