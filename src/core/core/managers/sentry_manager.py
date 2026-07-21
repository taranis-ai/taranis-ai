from typing import Any

import sentry_sdk

from core.config import Config


def initialize():
    if not Config.TARANIS_SENTRY_DSN:
        return

    sentry_options: dict[str, Any] = {
        "dsn": Config.TARANIS_SENTRY_DSN,
        "traces_sample_rate": 1.0,
        "profiles_sample_rate": 1.0,
    }
    if Config.SENTRY_ENABLE_LOGS:
        sentry_options["enable_logs"] = True
    if Config.SENTRY_SEND_DEFAULT_PII:
        sentry_options["send_default_pii"] = True
    if Config.SENTRY_ENABLE_DB_QUERY_SOURCE:
        sentry_options["enable_db_query_source"] = True

    sentry_sdk.init(**sentry_options)
