#!/usr/bin/env python3

import subprocess
import time

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


class RQRestartHandler(FileSystemEventHandler):
    def __init__(self):
        self.rq_process = None
        self.restart_rq()

    def restart_rq(self):
        if self.rq_process:
            self.rq_process.terminate()
            self.rq_process.wait()

        self.rq_process = subprocess.Popen(["python", "-m", "worker"])

    def on_modified(self, event):
        if event.is_directory:
            return
        self.restart_rq()


if __name__ == "__main__":
    print("Starting RQ worker in dev mode watching current directory for changes...")
    path = "."  # Watch the current directory, modify if necessary
    event_handler = RQRestartHandler()
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        event_handler.rq_process.terminate()
        event_handler.rq_process.wait()

    observer.join()
