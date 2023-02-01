from workers.config import get_settings


def main():
    redis = Redis()
    config = get_settings()
    queue = Queue(config.WORKER_TYPE, connection=redis)

    worker = Worker([queue], connection=redis, name=config.WORKER_NAME)
    worker.work()
