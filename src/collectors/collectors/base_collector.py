from taranisng.schema import collector, osint_source, news_item
from remote.core_api import CoreApi
from managers import time_manager
from taranisng.schema.parameter import Parameter, ParameterType
import datetime
from dateutil import tz


class BaseCollector:
    type = "BASE_COLLECTOR"
    name = "Base Collector"
    description = "Base abstract type for all collectors"

    parameters = [
        Parameter(0, "PROXY_SERVER", "Proxy server",
                  "Type SOCKS5 proxy server as username:password@ip:port or ip:port", ParameterType.STRING),
        Parameter(0, "REFRESH_INTERVAL", "Refresh Interval", "How often is this collector queried for new data",
                  ParameterType.NUMBER)
    ]

    def __init__(self):
        self.osint_sources = []

    def get_info(self):
        info_schema = collector.CollectorSchema()
        return info_schema.dump(self)

    def collect(self, source):
        pass

    @staticmethod
    def print_exception(source, error):
        print('OSINTSource ID: ' + source.id)
        print('OSINTSource name: ' + source.name)
        if str(error).startswith('b'):
            print('ERROR: ' + str(error)[2:-1])
        else:
            print('ERROR: ' + str(error))

    @staticmethod
    def timezone_info():
        timezone_info = {"A": tz.gettz("UTC +1"), "ACDT": tz.gettz("UTC +10:30"), "ACST": tz.gettz("UTC +9:30"),
                         "ACT": tz.gettz("UTC -5"), "ACWST": tz.gettz("UTC +8:45"), "ADT": tz.gettz("UTC +4"),
                         "AEDT": tz.gettz("UTC +11"), "AEST": tz.gettz("UTC +10"),
                         "AET": tz.gettz("UTC +10"), "AFT": tz.gettz("UTC +4:30"),
                         "AKDT": tz.gettz("UTC -8"), "AKST": tz.gettz("UTC -9"), "ALMT": tz.gettz("UTC +6"),
                         "AMST": tz.gettz("UTC -3"), "AMT": tz.gettz("UTC -4"), "ANAST": tz.gettz("UTC +12"),
                         "ANAT": tz.gettz("UTC +12"), "AQTT": tz.gettz("UTC +5"), "ART": tz.gettz("UTC -3"),
                         "AST": tz.gettz("UTC +3"), "AT": tz.gettz("UTC -4"), "AWDT": tz.gettz("UTC +9"),
                         "AWST": tz.gettz("UTC +8"), "AZOST": tz.gettz("UTC +0"), "AZOT": tz.gettz("UTC -1"),
                         "AZST": tz.gettz("UTC +5"), "AZT": tz.gettz("UTC +4"), "AoE": tz.gettz("UTC -12"),
                         "B": tz.gettz("UTC +2"), "BNT": tz.gettz("UTC +8"), "BOT": tz.gettz("UTC -4"),
                         "BRST": tz.gettz("UTC -2"), "BRT": tz.gettz("UTC -3"), "BST": tz.gettz("UTC +6"),
                         "BTT": tz.gettz("UTC +6"), "C": tz.gettz("UTC +3"), "CAST": tz.gettz("UTC +8"),
                         "CAT": tz.gettz("UTC +2"), "CCT": tz.gettz("UTC +6:30"), "CDT": tz.gettz("UTC -5"),
                         "CEST": tz.gettz("UTC +2"), "CET": tz.gettz("UTC +1"), "CHADT": tz.gettz("UTC +13:45"),
                         "CHAST": tz.gettz("UTC +12:45"), "CHOST": tz.gettz("UTC +9"), "CHOT": tz.gettz("UTC +8"),
                         "CHUT": tz.gettz("UTC +10"), "CIDST": tz.gettz("UTC -4"), "CIST": tz.gettz("UTC -5"),
                         "CKT": tz.gettz("UTC -10"), "CLST": tz.gettz("UTC -3"), "CLT": tz.gettz("UTC -4"),
                         "COT": tz.gettz("UTC -5"), "CST": tz.gettz("UTC -6"), "CT": tz.gettz("UTC -6"),
                         "CVT": tz.gettz("UTC -1"), "CXT": tz.gettz("UTC +7"), "CHST": tz.gettz("UTC +10"),
                         "D": tz.gettz("UTC +4"), "DAVT": tz.gettz("UTC +7"), "DDUT": tz.gettz("UTC +10"),
                         "E": tz.gettz("UTC +5"), "EASST": tz.gettz("UTC -5"), "EAST": tz.gettz("UTC -6"),
                         "EAT": tz.gettz("UTC +3"), "ECT": tz.gettz("UTC -5"), "EDT": tz.gettz("UTC -4"),
                         "EEST": tz.gettz("UTC +3"), "EET": tz.gettz("UTC +2"), "EGST": tz.gettz("UTC +0"),
                         "EGT": tz.gettz("UTC -1"), "EST": tz.gettz("UTC -5"), "ET": tz.gettz("UTC -5"),
                         "F": tz.gettz("UTC +6"), "FET": tz.gettz("UTC +3"), "FJST": tz.gettz("UTC +13"),
                         "FJT": tz.gettz("UTC +12"), "FKST": tz.gettz("UTC -3"), "FKT": tz.gettz("UTC -4"),
                         "FNT": tz.gettz("UTC -2"), "G": tz.gettz("UTC +7"), "GALT": tz.gettz("UTC -6"),
                         "GAMT": tz.gettz("UTC -9"), "GET": tz.gettz("UTC +4"), "GFT": tz.gettz("UTC -3"),
                         "GILT": tz.gettz("UTC +12"), "GMT": tz.gettz("UTC +0"), "GST": tz.gettz("UTC +4"),
                         "GYT": tz.gettz("UTC -4"), "H": tz.gettz("UTC +8"), "HDT": tz.gettz("UTC -9"),
                         "HKT": tz.gettz("UTC +8"), "HOVST": tz.gettz("UTC +8"), "HOVT": tz.gettz("UTC +7"),
                         "HST": tz.gettz("UTC -10"), "I": tz.gettz("UTC +9"), "ICT": tz.gettz("UTC +7"),
                         "IDT": tz.gettz("UTC +3"), "IOT": tz.gettz("UTC +6"), "IRDT": tz.gettz("UTC +4:30"),
                         "IRKST": tz.gettz("UTC +9"), "IRKT": tz.gettz("UTC +8"), "IRST": tz.gettz("UTC +3:30"),
                         "IST": tz.gettz("UTC +5:30"), "JST": tz.gettz("UTC +9"), "K": tz.gettz("UTC +10"),
                         "KGT": tz.gettz("UTC +6"), "KOST": tz.gettz("UTC +11"), "KRAST": tz.gettz("UTC +8"),
                         "KRAT": tz.gettz("UTC +7"), "KST": tz.gettz("UTC +9"), "KUYT": tz.gettz("UTC +4"),
                         "L": tz.gettz("UTC +11"), "LHDT": tz.gettz("UTC +11"), "LHST": tz.gettz("UTC +10:30"),
                         "LINT": tz.gettz("UTC +14"), "M": tz.gettz("UTC +12"), "MAGST": tz.gettz("UTC +12"),
                         "MAGT": tz.gettz("UTC +11"), "MART": tz.gettz("UTC -9:30"), "MAWT": tz.gettz("UTC +5"),
                         "MDT": tz.gettz("UTC -6"), "MHT": tz.gettz("UTC +12"), "MMT": tz.gettz("UTC +6:30"),
                         "MSD": tz.gettz("UTC +4"), "MSK": tz.gettz("UTC +3"), "MST": tz.gettz("UTC -7"),
                         "MT": tz.gettz("UTC -7"), "MUT": tz.gettz("UTC +4"), "MVT": tz.gettz("UTC +5"),
                         "MYT": tz.gettz("UTC +8"), "N": tz.gettz("UTC -1"), "NCT": tz.gettz("UTC +11"),
                         "NDT": tz.gettz("UTC -2:30"), "NFT": tz.gettz("UTC +11"), "NOVST": tz.gettz("UTC +7"),
                         "NOVT": tz.gettz("UTC +7"), "NPT": tz.gettz("UTC +5:45"), "NRT": tz.gettz("UTC +12"),
                         "NST": tz.gettz("UTC -3:30"), "NUT": tz.gettz("UTC -11"), "NZDT": tz.gettz("UTC +13"),
                         "NZST": tz.gettz("UTC +12"), "O": tz.gettz("UTC -2"), "OMSST": tz.gettz("UTC +7"),
                         "OMST": tz.gettz("UTC +6"), "ORAT": tz.gettz("UTC +5"), "P": tz.gettz("UTC -3"),
                         "PDT": tz.gettz("UTC -7"), "PET": tz.gettz("UTC -5"), "PETST": tz.gettz("UTC +12"),
                         "PETT": tz.gettz("UTC +12"), "PGT": tz.gettz("UTC +10"), "PHOT": tz.gettz("UTC +13"),
                         "PHT": tz.gettz("UTC +8"), "PKT": tz.gettz("UTC +5"), "PMDT": tz.gettz("UTC -2"),
                         "PMST": tz.gettz("UTC -3"), "PONT": tz.gettz("UTC +11"), "PST": tz.gettz("UTC -8"),
                         "PT": tz.gettz("UTC -8"), "PWT": tz.gettz("UTC +9"), "PYST": tz.gettz("UTC -3"),
                         "PYT": tz.gettz("UTC -4"), "Q": tz.gettz("UTC -4"), "QYZT": tz.gettz("UTC +6"),
                         "R": tz.gettz("UTC -5"), "RET": tz.gettz("UTC +4"), "ROTT": tz.gettz("UTC -3"),
                         "S": tz.gettz("UTC -6"), "SAKT": tz.gettz("UTC +11"), "SAMT": tz.gettz("UTC +4"),
                         "SAST": tz.gettz("UTC +2"), "SBT": tz.gettz("UTC +11"), "SCT": tz.gettz("UTC +4"),
                         "SGT": tz.gettz("UTC +8"), "SRET": tz.gettz("UTC +11"), "SRT": tz.gettz("UTC -3"),
                         "SST": tz.gettz("UTC -11"), "SYOT": tz.gettz("UTC +3"), "T": tz.gettz("UTC -7"),
                         "TAHT": tz.gettz("UTC -10"), "TFT": tz.gettz("UTC +5"), "TJT": tz.gettz("UTC +5"),
                         "TKT": tz.gettz("UTC +13"), "TLT": tz.gettz("UTC +9"), "TMT": tz.gettz("UTC +5"),
                         "TOST": tz.gettz("UTC +14"), "TOT": tz.gettz("UTC +13"), "TRT": tz.gettz("UTC +3"),
                         "TVT": tz.gettz("UTC +12"), "U": tz.gettz("UTC -8"), "ULAST": tz.gettz("UTC +9"),
                         "ULAT": tz.gettz("UTC +8"), "UTC": tz.gettz("UTC"), "UYST": tz.gettz("UTC -2"),
                         "UYT": tz.gettz("UTC -3"), "UZT": tz.gettz("UTC +5"), "V": tz.gettz("UTC -9"),
                         "VET": tz.gettz("UTC -4"), "VLAST": tz.gettz("UTC +11"), "VLAT": tz.gettz("UTC +10"),
                         "VOST": tz.gettz("UTC +6"), "VUT": tz.gettz("UTC +11"), "W": tz.gettz("UTC -10"),
                         "WAKT": tz.gettz("UTC +12"), "WARST": tz.gettz("UTC -3"), "WAST": tz.gettz("UTC +2"),
                         "WAT": tz.gettz("UTC +1"), "WEST": tz.gettz("UTC +1"), "WET": tz.gettz("UTC +0"),
                         "WFT": tz.gettz("UTC +12"), "WGST": tz.gettz("UTC -2"), "WGT": tz.gettz("UTC -3"),
                         "WIB": tz.gettz("UTC +7"), "WIT": tz.gettz("UTC +9"), "WITA": tz.gettz("UTC +8"),
                         "WST": tz.gettz("UTC +14"), "WT": tz.gettz("UTC +0"), "X": tz.gettz("UTC -11"),
                         "Y": tz.gettz("UTC -12"), "YAKST": tz.gettz("UTC +10"), "YAKT": tz.gettz("UTC +9"),
                         "YAPT": tz.gettz("UTC +10"), "YEKST": tz.gettz("UTC +6"), "YEKT": tz.gettz("UTC +5"),
                         "Z": tz.gettz("UTC +0")}
        return timezone_info

    @staticmethod
    def history(interval):
        if interval[0].isdigit() and ':' in interval:
            limit = datetime.datetime.now() - datetime.timedelta(days=1)
        elif interval[0].isalpha():
            limit = datetime.datetime.now() - datetime.timedelta(weeks=1)
        else:
            if int(interval) > 60:
                hours = int(interval) // 60
                minutes = int(interval) - hours * 60
                limit = datetime.datetime.now() - datetime.timedelta(days=0, hours=hours, minutes=minutes)
            else:
                limit = datetime.datetime.now() - datetime.timedelta(days=0, hours=0, minutes=int(interval))

        return limit

    @staticmethod
    def filter_by_word_list(news_items, source):

        if source.word_lists:
            one_word_list = set()

            for word_list in source.word_lists:
                if word_list.use_for_stop_words is False:
                    for category in word_list.categories:
                        for entry in category.entries:
                            one_word_list.add(entry.value.lower())

            filtered_news_items = []
            if one_word_list:
                for item in news_items:
                    for word in one_word_list:
                        if word in item.title.lower() or word in item.review.lower() or word in item.content.lower():
                            filtered_news_items.append(item)
                            break

                return filtered_news_items
            else:
                return news_items
        else:
            return news_items

    @staticmethod
    def publish(news_items, source):
        filtered_news_items = BaseCollector.filter_by_word_list(news_items, source)
        news_items_schema = news_item.NewsItemDataSchema(many=True)
        CoreApi.add_news_items(news_items_schema.dump(filtered_news_items))

    def initialize(self):
        response, code = CoreApi.get_osint_sources(self.type)
        if code == 200 and response is not None:
            source_schema = osint_source.OSINTSourceSchemaBase(many=True)
            self.osint_sources = source_schema.load(response)

            for source in self.osint_sources:
                self.collect(source)
                interval = source.parameter_values["REFRESH_INTERVAL"]

                if interval != '':
                    if interval[0].isdigit() and ':' in interval:
                        time_manager.schedule_job_every_day(interval, self.collect, source)
                    elif interval[0].isalpha():
                        interval = interval.split(',')
                        day = interval[0].strip()
                        at = interval[1].strip()
                        if day == 'Monday':
                            time_manager.schedule_job_on_monday(at, self.collect, source)
                        elif day == 'Tuesday':
                            time_manager.schedule_job_on_tuesday(at, self.collect, source)
                        elif day == 'Wednesday':
                            time_manager.schedule_job_on_wednesday(at, self.collect, source)
                        elif day == 'Thursday':
                            time_manager.schedule_job_on_thursday(at, self.collect, source)
                        elif day == 'Friday':
                            time_manager.schedule_job_on_friday(at, self.collect, source)
                        elif day == 'Saturday':
                            time_manager.schedule_job_on_saturday(at, self.collect, source)
                        else:
                            time_manager.schedule_job_on_sunday(at, self.collect, source)
                    else:
                        time_manager.schedule_job_minutes(int(interval), self.collect, source)
