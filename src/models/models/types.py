from enum import StrEnum, auto, IntEnum


class TLPLevel(StrEnum):
    CLEAR = "clear"
    GREEN = "green"
    AMBER_STRICT = "amber+strict"
    AMBER = "amber"
    RED = "red"


class ItemType(StrEnum):
    OSINT_SOURCE = auto()
    OSINT_SOURCE_GROUP = auto()
    WORD_LIST = auto()
    REPORT_ITEM_TYPE = auto()
    PRODUCT_TYPE = auto()

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            for member in cls:
                if value.upper() == member.name:
                    return member
        return super()._missing_(value)


class COLLECTOR_TYPES(StrEnum):
    RSS_COLLECTOR = auto()
    EMAIL_COLLECTOR = auto()
    TWITTER_COLLECTOR = auto()
    SIMPLE_WEB_COLLECTOR = auto()
    RT_COLLECTOR = auto()
    MISP_COLLECTOR = auto()
    MANUAL_COLLECTOR = auto()

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            for member in cls:
                if value.upper() == member.name:
                    return member
        return super()._missing_(value)


class BOT_TYPES(StrEnum):
    ANALYST_BOT = auto()
    GROUPING_BOT = auto()
    NLP_BOT = auto()
    IOC_BOT = auto()
    TAGGING_BOT = auto()
    STORY_BOT = auto()
    SUMMARY_BOT = auto()
    WORDLIST_BOT = auto()
    SENTIMENT_ANALYSIS_BOT = auto()
    CYBERSEC_CLASSIFIER_BOT = auto()

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            for member in cls:
                if value.upper() == member.name:
                    return member
        return super()._missing_(value)


class PRESENTER_TYPES(StrEnum):
    PDF_PRESENTER = auto()
    HTML_PRESENTER = auto()
    TEXT_PRESENTER = auto()
    JSON_PRESENTER = auto()

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            for member in cls:
                if value.upper() == member.name:
                    return member
        return super()._missing_(value)


class PUBLISHER_TYPES(StrEnum):
    FTP_PUBLISHER = auto()
    SFTP_PUBLISHER = auto()
    EMAIL_PUBLISHER = auto()
    WORDPRESS_PUBLISHER = auto()
    MISP_PUBLISHER = auto()

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            for member in cls:
                if value.upper() == member.name:
                    return member
        return super()._missing_(value)


class WORKER_TYPES(StrEnum):
    RSS_COLLECTOR = auto()
    EMAIL_COLLECTOR = auto()
    TWITTER_COLLECTOR = auto()
    SIMPLE_WEB_COLLECTOR = auto()
    MANUAL_COLLECTOR = auto()
    RT_COLLECTOR = auto()
    MISP_COLLECTOR = auto()
    ANALYST_BOT = auto()
    GROUPING_BOT = auto()
    NLP_BOT = auto()
    IOC_BOT = auto()
    TAGGING_BOT = auto()
    STORY_BOT = auto()
    SUMMARY_BOT = auto()
    SENTIMENT_ANALYSIS_BOT = auto()
    CYBERSEC_CLASSIFIER_BOT = auto()
    WORDLIST_BOT = auto()
    PDF_PRESENTER = auto()
    HTML_PRESENTER = auto()
    TEXT_PRESENTER = auto()
    JSON_PRESENTER = auto()
    FTP_PUBLISHER = auto()
    SFTP_PUBLISHER = auto()
    EMAIL_PUBLISHER = auto()
    WORDPRESS_PUBLISHER = auto()
    MISP_PUBLISHER = auto()
    MISP_CONNECTOR = auto()

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            for member in cls:
                if value.upper() == member.name:
                    return member
        return super()._missing_(value)


class CONNECTOR_TYPES(StrEnum):
    MISP_CONNECTOR = auto()

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            for member in cls:
                if value.upper() == member.name:
                    return member
        return super()._missing_(value)


class WORKER_CATEGORY(StrEnum):
    COLLECTOR = auto()
    BOT = auto()
    PRESENTER = auto()
    PUBLISHER = auto()
    CONNECTOR = auto()

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            for member in cls:
                if value.upper() == member.name:
                    return member
        return super()._missing_(value)


class WordListUsage(IntEnum):
    COLLECTOR_INCLUDELIST = 1  # 2^0
    COLLECTOR_EXCLUDELIST = 2  # 2^1
    TAGGING_BOT = 4  # 2^2


class OSINTState(IntEnum):
    DISABLED = -2
    UNKNOWN = -1
    OK = 0
    ERROR = 1


class AttributeType(StrEnum):
    STRING = auto()
    NUMBER = auto()
    BOOLEAN = auto()
    RADIO = auto()
    ENUM = auto()
    TEXT = auto()
    RICH_TEXT = auto()
    DATE = auto()
    TIME = auto()
    DATE_TIME = auto()
    LINK = auto()
    ATTACHMENT = auto()
    TLP = auto()
    CPE = auto()
    CVE = auto()
    CVSS = auto()
    STORY = auto()

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            for member in cls:
                if value.upper() == member.name:
                    return member
        return super()._missing_(value)
