import io
from datetime import datetime, timezone
from typing import Any

from flask import Response, send_file
from models.admin import ExportStoriesQuery
from pydantic import ValidationError
from werkzeug.datastructures import MultiDict

from core.log import logger
from core.service.story import StoryService


class AdminService:
    @staticmethod
    def _build_export_filename() -> str:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        return f"story_export_{timestamp}.json"

    @classmethod
    def export_stories(cls, request_args: MultiDict[str, str]) -> Response | tuple[dict[str, Any], int]:
        try:
            query = ExportStoriesQuery.model_validate(request_args.to_dict())
        except ValidationError as exc:
            errors = exc.errors(include_url=False)
            logger.warning(f"Invalid export stories query: {errors}")
            return {"error": errors}, 400

        try:
            export_method = StoryService.export_with_metadata if query.metadata else StoryService.export
            data = export_method(query.timefrom, query.timeto)
        except Exception:
            logger.exception("Failed to export stories")
            return {"error": "Failed to export stories"}, 500

        if data is None:
            logger.error("Story export returned no data")
            return {"error": "Unable to export"}, 400

        if not isinstance(data, (bytes, bytearray)):
            logger.error(f"Story export returned invalid payload type: {type(data)}")
            return {"error": "Failed to export stories"}, 500

        return send_file(
            io.BytesIO(bytes(data)),
            download_name=cls._build_export_filename(),
            mimetype="application/json",
            as_attachment=True,
        )
