from datetime import datetime, timezone
import json
from uuid import uuid4
from worker.connectors.base_misp_builder import BaseMISPBuilder
from misp_stix_converter import MISPtoSTIX21Parser
from worker.log import logger
from .base_presenter import BasePresenter


TYPE_MAP = {
    "TLP": "text",
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
    "Rich Text": "comment",
    "Attachment": "attachment",
    "MISP Attribute Type": None,
    "MISP Attribute Category": None,
    "MISP Attribute Distribution": None,
    "MISP Event Distribution": None,
    "MISP Event Analysis": None,
    "MISP Event Threat Level": None,
}


class STIXPresenter(BaseMISPBuilder, BasePresenter):
    def __init__(self):
        super().__init__()
        self.type = "STIX_PRESENTER"
        self.name = "STIX Presenter"
        self.description = "STIX presenter to export reports into STIX Report format"

    def generate(self, product: dict, template: str | None, parameters: dict[str, str] | None = None) -> str | None:
        report_ids = product.get("report_items", [])
        logger.info(f"Sending reports to STIX: {report_ids}")
        return self.export_to_stix(report_ids) or None

    def export_to_stix(self, report_items: list[dict] | None) -> str:
        if not report_items:
            logger.warning("No report items provided.")
            return json.dumps({"type": "bundle", "id": f"bundle--{uuid4()}", "spec_version": "2.1", "objects": []}, indent=2)

        stix_data = []
        for report_item in report_items:
            logger.debug(f"{report_item=}")
            stix_data.extend(json.loads(self.convert_to_stix(report_item)))
            logger.debug(f"Converted Report ID {report_item['id']} to STIX")

        bundle = {
            "type": "bundle",
            "id": f"bundle--{uuid4()}",
            "spec_version": "2.1",
            "objects": stix_data,
        }
        return json.dumps(bundle, indent=2)

    def convert_to_stix(self, report_item: dict) -> str:
        event = self.create_misp_event(report_item, sharing_group_id=None, distribution="1")
        # A published MISP event with a timestamp is converted to a STIX report
        event.published = True
        event.publish_timestamp = int(datetime.now(timezone.utc).timestamp())

        for key, value in report_item.get("attributes", {}).items():
            if not key or not value:
                continue

            group_title, attr_name = key.split("_", 1)
            misp_type = TYPE_MAP.get(attr_name, "text")

            event.add_attribute(
                type=misp_type,
                category="External analysis",
                value=value,
            )

        for story in report_item.get("stories", []):
            self.add_story_properties_to_event(story, event)

        parser = MISPtoSTIX21Parser()
        parser.parse_misp_event(event)
        stix_objects = [json.loads(obj.serialize()) for obj in parser.stix_objects]
        return json.dumps(stix_objects)
