import time
from datetime import datetime
from flask_jwt_extended import verify_jwt_in_request

from flask import Response, stream_with_context, Flask
from core.managers.sse_manager import sse_manager
from core.managers.log_manager import logger


def stream():
    messages = sse_manager.sse.listen()
    time.sleep(0.5)
    yield sse_manager.sse.format_sse(data={"connected": f"{datetime.now().isoformat()}"}, event="connected")
    while True:
        yield messages.get()


def sse_request():
    try:
        verify_jwt_in_request()
        return Response(stream_with_context(stream()), mimetype="text/event-stream")
    except Exception as e:
        logger.error(f"Error in sse_request: {e}")
        return str(e), 500


def initialize(app: Flask):
    app.add_url_rule("/sse", "sse", sse_request)
