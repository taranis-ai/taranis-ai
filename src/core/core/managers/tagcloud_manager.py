from core.managers import time_manager
from core.model.tag_cloud import TagCloud


def job(app):
    with app.app_context():
        TagCloud.delete_words()


def initialize(app):
    time_manager.schedule_job_every_day("00:01", job, app)
