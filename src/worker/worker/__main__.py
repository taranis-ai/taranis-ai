# from worker import CeleryWorker

# cw = CeleryWorker()
# celery = cw.app

from worker import repo_info

print("Starting prefect worker...")
repo_info()
