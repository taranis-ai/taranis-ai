from flask import Flask, Response, current_app, request


def init_app(app: Flask) -> None:
    app.config.update(
        JWT_COOKIE_SECURE=not app.debug,
        SESSION_COOKIE_SECURE=not app.debug,
        JWT_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_HTTPONLY=True,
    )
    app.after_request(set_security_headers)


def set_security_headers(response: Response) -> Response:
    if current_app.debug:
        return response

    response.headers.setdefault("Strict-Transport-Security", "max-age=31536000")
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    # Published reports already have their own sandbox policy.
    response.headers.setdefault("Content-Security-Policy", "default-src 'none'; base-uri 'none'; frame-ancestors 'self'")
    if request.endpoint != "static" and request.blueprint != "static":
        response.headers["Cache-Control"] = "no-store"
    return response
