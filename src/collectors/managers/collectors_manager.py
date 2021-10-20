import threading

from collectors.atom_collector import AtomCollector
from collectors.email_collector import EmailCollector
from collectors.manual_collector import ManualCollector
from collectors.rss_collector import RSSCollector
from collectors.scheduled_tasks_collector import ScheduledTasksCollector
from collectors.slack_collector import SlackCollector
from collectors.twitter_collector import TwitterCollector
from collectors.web_collector import WebCollector

collectors = {}


def initialize():
    register_collector(RSSCollector())
    register_collector(WebCollector())
    register_collector(TwitterCollector())
    register_collector(EmailCollector())
    register_collector(SlackCollector())
    register_collector(AtomCollector())
    register_collector(ManualCollector())
    register_collector(ScheduledTasksCollector())


def register_collector(collector):
    collectors[collector.type] = collector

    class InitializeThread(threading.Thread):
        @classmethod
        def run(cls):
            collector.initialize()

    initialize_thread = InitializeThread()
    initialize_thread.start()


def refresh_collector(collector_type):
    if collector_type in collectors:
        class RefreshThread(threading.Thread):
            @classmethod
            def run(cls):
                collectors[collector_type].refresh()

        refresh_thread = RefreshThread()
        refresh_thread.start()
        return 200
    else:
        return 403


def get_registered_collectors_info(id):
    with open('/app/storage/id.txt', 'w') as file:
        file.write(id)

    collectors_info = []
    for key in collectors:
        collectors_info.append(collectors[key].get_info())

    return collectors_info
