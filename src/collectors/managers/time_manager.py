import threading
import schedule
import time


def schedule_job_every_day(interval, job_func, *args, **kwargs):
    return schedule.every().day.at(interval).do(job_func, *args, **kwargs)


def schedule_job_minutes(interval, job_func, *args, **kwargs):
    return schedule.every(interval).minutes.do(job_func, *args, **kwargs)


def schedule_job_on_monday(interval, job_func, *args, **kwargs):
    return schedule.every().monday.at(interval).do(job_func, *args, **kwargs)


def schedule_job_on_tuesday(interval, job_func, *args, **kwargs):
    return schedule.every().tuesday.at(interval).do(job_func, *args, **kwargs)


def schedule_job_on_wednesday(interval, job_func, *args, **kwargs):
    return schedule.every().wednesday.at(interval).do(job_func, *args, **kwargs)


def schedule_job_on_thursday(interval, job_func, *args, **kwargs):
    return schedule.every().thursday.at(interval).do(job_func, *args, **kwargs)


def schedule_job_on_friday(interval, job_func, *args, **kwargs):
    return schedule.every().friday.at(interval).do(job_func, *args, **kwargs)


def schedule_job_on_saturday(interval, job_func, *args, **kwargs):
    return schedule.every().saturday.at(interval).do(job_func, *args, **kwargs)


def schedule_job_on_sunday(interval, job_func, *args, **kwargs):
    return schedule.every().sunday.at(interval).do(job_func, *args, **kwargs)


def cancel_job(scheduler_job):
    schedule.cancel_job(scheduler_job)


def run_scheduler():
    scheduler_event = threading.Event()

    class ScheduleThread(threading.Thread):
        @classmethod
        def run(cls):
            while not scheduler_event.is_set():
                schedule.run_pending()
                time.sleep(1)

    scheduler_thread = ScheduleThread()
    scheduler_thread.start()

    return scheduler_event


scheduler_stop_handler = run_scheduler()
