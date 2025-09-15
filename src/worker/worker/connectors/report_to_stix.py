from datetime import datetime, timezone
from worker.connectors.base_misp_builder import BaseMispBuilder
from misp_stix_converter import MISPtoSTIX21Parser
from worker.log import logger

TYPE_MAP = {
    "CVSS": "text",
    "TEXT": "text",
    "TIME": "text",
    "ENUM": "text",
    "RADIO": "text",
    "Story": "text",
    "STRING": "text",
    "Impact": "text",
    "NIS Sectors": "text",
    "Disinfo type": "text",
    "Confidentiality": "text",
    "Source Reliability": "text",
    "Information Credibility": "text",
    "TEXT AREA": "comment",
    "NUMBER": "float",
    "FLOAT": "float",
    "DATE": "date",
    "DATETIME": "datetime",
    "BOOLEAN": "boolean",
    "LINK": "link",
    "CVE": "vulnerability",
    "CPE": "cpe",
    "TLP": "tlp",
    "Rich Text": "comment",
    "Attachment": "attachment",
    "MISP Attribute Type": None,
    "MISP Attribute Category": None,
    "MISP Attribute Distribution": None,
    "MISP Event Distribution": None,
    "MISP Event Analysis": None,
    "MISP Event Threat Level": None,
}


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
                logger.debug(f"{report_item=}")
                stix_data = self.convert_to_stix(report_item)
                logger.debug(f"Converted Report ID {report_id} to STIX: {stix_data}")
            else:
                logger.warning(f"Report item with ID {report_id} not found.")

    def convert_to_stix(self, report_item: dict) -> list:
        event = self.create_misp_event(report_item, sharing_group_id=None, distribution="1")
        # A published MISP event with a timestamp is converted to a STIX report
        event.published = True
        event.publish_timestamp = int(datetime.now(timezone.utc).timestamp())

        for attr in report_item.get("attributes", []):
            title = attr.get("title")
            value = attr.get("value")
            if not title or not value:
                continue

            group_title = attr.get("group_title", "Metadata")
            taranis_type = attr.get("type", "STRING")
            misp_type = TYPE_MAP.get(taranis_type, "text")

            event.add_attribute(
                type=misp_type,
                category="External analysis",
                value=value,
                comment=f"{group_title}: {title}",
            )

        for story in report_item.get("stories", []):
            self.add_story_properties_to_event(story, event)

        parser = MISPtoSTIX21Parser()
        parser.parse_misp_event(event)
        return parser.stix_objects
