import sentry_sdk


def initialize(app):
    sentry_sdk.init(
        dsn=app.config.get("SENTRY_DSN"),
        traces_sample_rate=app.config.get("SENTRY_TRACES_SAMPLE_RATE"),
        profiles_sample_rate=app.config.get("SENTRY_PROFILES_SAMPLE_RATE"),
    )
