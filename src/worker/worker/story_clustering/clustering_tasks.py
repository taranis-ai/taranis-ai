from celery import shared_task
import jsonpickle
from celery import current_app


@shared_task(name="initial_clustering")
def initial_clustering(corpus_encoded):
    corpus = jsonpickle.decode(corpus_encoded)
    story_bot = current_app.tasks.get("bot_task").bots.get("story_bot")
    story_bot.initial_clustering_event_handler(corpus)
