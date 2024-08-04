from celery import shared_task
from celery import current_app
import json
from story_clustering.document_representation import Corpus


@shared_task(name="initial_clustering")
def initial_clustering(corpus_encoded):
    corpus_dict = json.loads(corpus_encoded)
    corpus = Corpus(**corpus_dict)
    story_bot = current_app.tasks.get("bot_task").bots.get("story_bot")
    return story_bot.initial_clustering_event_handler(corpus)
