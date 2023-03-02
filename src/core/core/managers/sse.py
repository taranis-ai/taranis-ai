import queue
import json
from flask import g


class SSE:
    def __init__(self):
        self.listeners = []

    def listen(self):
        q = queue.Queue(maxsize=20)
        self.listeners.append(q)
        return q

    def publish(self, data: str | dict, event=None):
        msg = self.format_sse(data, event)
        for i in reversed(range(len(self.listeners))):
            try:
                self.listeners[i].put_nowait(msg)
            except queue.Full:
                del self.listeners[i]

    def format_sse(self, data: str | dict, event=None) -> str:
        """Formats a string and an event name in order to follow the event stream convention.
        https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events#event_stream_format
        >>> format_sse(data=json.dumps({'abc': 123}), event='Jackson 5')
        'event: Jackson 5\\ndata: {"abc": 123}\\n\\n'
        """
        if isinstance(data, dict):
            data = json.dumps(data)
        msg = f"data: {data}\n\n"
        if event is not None:
            msg = f"event: {event}\n{msg}"
        return msg
