import sentry_sdk


def initialize(app):
    sentry_sdk.init(
        dsn=app.config.get("SENTRY_DSN"),
        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for tracing.
        traces_sample_rate=app.config.get("SENTRY_TRACES_SAMPLE_RATE"),
        # Set profiles_sample_rate to 1.0 to profile 100%
        # of sampled transactions.
        # We recommend adjusting this value in production.
        profiles_sample_rate=app.config.get("SENTRY_PROFILES_SAMPLE_RATE"),
    )
