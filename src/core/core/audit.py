from core.log import TaranisLogger
from core.config import Config


class AuditLogger(TaranisLogger):
    def __init__(self, syslog_address=None):
        super().__init__(module="audit", debug=Config.DEBUG, colored=Config.COLORED_LOGS, syslog_address=syslog_address)


audit_logger = AuditLogger()
