import os
import threading
import time

from managers.log_manager import log_debug, log_system_activity
from collectors.atom_collector import AtomCollector
from collectors.email_collector import EmailCollector
from collectors.manual_collector import ManualCollector
from collectors.rss_collector import RSSCollector
from collectors.scheduled_tasks_collector import ScheduledTasksCollector
from collectors.slack_collector import SlackCollector
from collectors.twitter_collector import TwitterCollector
from collectors.web_collector import WebCollector
from remote.core_api import CoreApi

collectors = {}
status_report_thread = None

def reportStatus():
    while True:
        log_debug("[{}] Sending status update...".format(__name__))
        response, code = CoreApi.update_collector_status()
        log_debug("[{}] Core responded with: HTTP {}, {}".format(__name__, code, response))
        time.sleep(55)

def initialize():
    log_system_activity(__name__, "Initializing collector...")

    # inform core that this collector node is alive
    status_report_thread = threading.Thread(target=reportStatus)
    status_report_thread.daemon = True
    status_report_thread.start()

    register_collector(RSSCollector())
    register_collector(WebCollector())
    register_collector(TwitterCollector())
    register_collector(EmailCollector())
    register_collector(SlackCollector())
    register_collector(AtomCollector())
    register_collector(ManualCollector())
    register_collector(ScheduledTasksCollector())

    log_system_activity(__name__, "Collector initialized.")

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
    config_file = os.getenv('COLLECTOR_CONFIG_FILE')
    with open(config_file, 'w') as file:
        file.write(id)

    collectors_info = []
    for key in collectors:
        collectors_info.append(collectors[key].get_info())

    return collectors_info
