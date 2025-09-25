from flask import Response

from core.model.report_item import ReportItem


class ReportItemService:
    @classmethod
    def get_render(cls, report_id: str):
        if report_data := ReportItem.get_render(report_id):
            return Response(
                report_data["blob"],
                mimetype=report_data["mime_type"],
                headers={"Content-Disposition": f"attachment; filename=report-{report_id}.json"},
            )
        return {"error": f"Report {report_id} not found"}, 404
