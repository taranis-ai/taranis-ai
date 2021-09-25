from collectors.rss_collector import RSSCollector
from collectors.web_collector import WebCollector
from collectors.twitter_collector import TwitterCollector
from collectors.email_collector import EmailCollector
from collectors.slack_collector import SlackCollector
from collectors.atom_collector import AtomCollector
from collectors.manual_collector import ManualCollector
from collectors.scheduled_tasks_collector import ScheduledTasksCollector

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
    collector.initialize()


def get_registered_collectors_info():
    collectors_info = []
    for key in collectors:
        collectors_info.append(collectors[key].get_info())

    return collectors_info
