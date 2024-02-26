from celery import shared_task
import worker.bots
from worker.log import logger
import jsonpickle


@shared_task(name="initial_clustering")
def initial_clustering(corpus_encoded):
    corpus = jsonpickle.decode(corpus_encoded)
    story_bot = worker.bots.StoryBot()
    story_bot.initial_clustering_event_handler(corpus)
