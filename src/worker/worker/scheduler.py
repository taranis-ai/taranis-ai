import time
from celery.beat import Scheduler, ScheduleEntry
from datetime import datetime, timezone
from worker.log import logger

from worker.core_api import CoreApi


class RESTScheduleEntry(ScheduleEntry):
    def is_due(self):
        return super().is_due()

    def next(self):
        return super().next()


class RESTScheduler(Scheduler):
    Entry = RESTScheduleEntry
    schedule_from_core = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.core_api = CoreApi()
        self.last_checked = datetime.now(timezone.utc)
        self.max_interval = 60

    def update_schedule_from_core(self):
        if not (core_schedule := self.core_api.get_schedule()):
            return
        for entry in core_schedule:
            entry["app"] = self.app
            if last_run_at := entry.get("last_run_at"):
                entry["last_run_at"] = datetime.fromisoformat(last_run_at)
            rest_entry = self.Entry(**entry)

            if schedule_entry := self.schedule.get(entry["name"]):
                if rest_entry.schedule != schedule_entry.schedule:
                    logger.debug(f"Changed schedule of {entry['name']}")
                    self.schedule[entry["name"]] = rest_entry
            else:
                logger.debug(f"Adding new entry: {rest_entry}")
                self.schedule[entry["name"]] = rest_entry
        return self.schedule

    def sync(self):
        current_datetime = datetime.now()
        estimates = {}
        for s in self.schedule.values():
            try:
                estimate = s.schedule.remaining_estimate(s.last_run_at)
                next_run_time = current_datetime + estimate
                estimates[s.name] = next_run_time.isoformat()
            except Exception:
                logger.log_debug_trace(f"Failed to sync {s.name}")
        # logger.debug(f"Updating next run times: {estimates}")
        self.core_api.update_next_run_time(estimates)

    def get_schedule(self):
        return self.schedule_from_core

    def set_schedule(self, schedule):
        self.schedule_from_core = schedule

    schedule = property(get_schedule, set_schedule)

    def tick(self):
        now = datetime.now(timezone.utc)
        if (now - self.last_checked).total_seconds() >= self.max_interval:
            self.last_checked = now
            self.update_schedule_from_core()
            self.sync()
        time.sleep(0.1)
        super().tick()
