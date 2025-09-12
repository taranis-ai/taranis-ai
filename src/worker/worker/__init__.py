from prefect import serve
from worker.tasks import setup_tasks


def main():
    tasks = setup_tasks()
    serve(*tasks)


if __name__ == "__main__":
    main()
