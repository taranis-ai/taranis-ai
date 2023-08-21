import time
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class CeleryRestartHandler(FileSystemEventHandler):
    def __init__(self):
        self.celery_process = None
        self.restart_celery()

    def restart_celery(self):
        if self.celery_process:
            self.celery_process.terminate()
            self.celery_process.wait()

        self.celery_process = subprocess.Popen(["celery", "-A", "worker", "worker"])

    def on_modified(self, event):
        if event.is_directory:
            return
        self.restart_celery()


if __name__ == "__main__":
    path = "."  # Watch the current directory, modify if necessary
    event_handler = CeleryRestartHandler()
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        event_handler.celery_process.terminate()
        event_handler.celery_process.wait()

    observer.join()
