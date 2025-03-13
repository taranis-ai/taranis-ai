from worker.config import Config
from worker.core_api import CoreApi

from worker.tasks import setup_tasks


def main():
    core_api = CoreApi()
    setup_tasks()


if __name__ == "worker":
    main()

