import os
import requests
import sseclient
import threading

from managers import bots_manager


def initialize():
    class SSEThread(threading.Thread):
        @classmethod
        def run(cls):
            try:
                response = requests.get(os.getenv("TARANIS_NG_CORE_SSE") + "?api_key=" + os.getenv("API_KEY"),
                                        stream=True)
                client = sseclient.SSEClient(response)
                for event in client.events():
                    bots_manager.process_event(event.event, event.data)

            except requests.exceptions.ConnectionError:
                print('Could not connect to Core SSE')

    sse_thread = SSEThread()
    sse_thread.start()
