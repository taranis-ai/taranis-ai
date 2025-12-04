from worker.collectors.rss_collector import RSSCollector
from worker.collectors.rt_collector import RTCollector
from worker.collectors.simple_web_collector import SimpleWebCollector
from worker.collectors.misp_collector import MispCollector

COLLECTOR_REGISTRY = {
    "rss_collector": RSSCollector,
    "rt_collector": RTCollector,
    "simple_web_collector": SimpleWebCollector,
    "misp_collector": MispCollector,
}
