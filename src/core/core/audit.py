from core.log import TaranisLogger
from core.config import Config
from flask import Response, request
from flask_jwt_extended import current_user


class AuditLogger(TaranisLogger):
    def __init__(self, syslog_address=None):
        super().__init__(module="audit", debug=Config.DEBUG, colored=Config.COLORED_LOGS, syslog_address=syslog_address)

    def after_request_audit_log(self, response: Response) -> Response:
        if request.method == "GET" and request.path == "/api/assess/stories":
            return self._log_audit_after_request(response, " accessed Stories: ")
        if request.method == "PUT" and request.path == "/api/assess/stories":
            return self._log_audit_after_request(response, " updated Stories: ")
        if request.method == "DELETE" and request.path == "/api/assess/stories":
            return self._log_audit_after_request(response, " deleted Stories: ")
        return response

    def _log_audit_after_request(self, response, arg1):
        story_items = response.get_json().get("items")
        if story_items and len(story_items) > 0:
            story_ids = [story["id"] for story in story_items]
            audit_logger.info(f"User with ID: {current_user.id}{arg1}{story_ids}")
        return response


audit_logger = AuditLogger()
