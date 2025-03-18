from worker.tasks import setup_tasks


def main():
    setup_tasks()


if __name__ == "worker":
    main()
