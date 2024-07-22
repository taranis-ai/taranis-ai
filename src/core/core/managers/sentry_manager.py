import sentry_sdk
from core.config import Config


def initialize():
    sentry_sdk.init(
        dsn=Config.TARANIS_CORE_SENTRY_DSN,
        traces_sample_rate=Config.SENTRY_TRACES_SAMPLE_RATE,
        profiles_sample_rate=Config.SENTRY_PROFILES_SAMPLE_RATE,
    )
