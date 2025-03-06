import sentry_sdk
from core.config import Config


def initialize():
    if not Config.TARANIS_CORE_SENTRY_DSN:
        return

    sentry_sdk.init(
        dsn=Config.TARANIS_CORE_SENTRY_DSN,
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
    )
