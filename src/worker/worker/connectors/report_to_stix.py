from worker.connectors.base_misp_builder import BaseMispBuilder
from misp_stix_converter import MISPtoSTIX21Parser

from worker.log import logger


class ReportToStix(BaseMispBuilder):
    def __init__(self):
        super().__init__()

    def execute(self, connector_config: list[str] | None, report_ids: list[str] | None) -> None:
        print(f"Sending data to STIX: {connector_config}")
        print(f"Sending reports to STIX: {report_ids}")
        self.export_to_stix(report_ids)

        return None

    def export_to_stix(self, report_ids: list[str] | None) -> None:
        if not report_ids:
            logger.warning("No report IDs provided.")
            return

        for report_id in report_ids:
            if report_item := self.core_api.get_report_item(report_id):
                stix_data = self.convert_to_stix(report_item)
                logger.debug(f"Converted Report ID {report_id} to STIX: {stix_data}")
            else:
                logger.warning(f"Report item with ID {report_id} not found.")

    def convert_to_stix(self, report_item: dict) -> list:
        event = self.create_misp_event(report_item, sharing_group_id=None, distribution="1")
        for story in report_item.get("stories", []):
            self.add_story_properties_to_event(story, event)

        parser = MISPtoSTIX21Parser()
        parser.parse_misp_event(event)

        return parser.stix_objects
