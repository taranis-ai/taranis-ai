import json
from copy import deepcopy
from datetime import datetime, timezone
from uuid import uuid4

from misp_stix_converter import MISPtoSTIX21Parser
from pymisp import MISPEvent

from worker.connectors import base_misp_builder
from worker.connectors.definitions.misp_objects import BaseMispObject
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


class STIXPresenter(BasePresenter):
    """
    Presenter that exports MISP-compatible reports into STIX 2.1 bundles.
    Uses base_misp_builder via composition to construct MISP events.
    """

    def __init__(self):
        super().__init__()
        self.type = "STIX_PRESENTER"
        self.name = "STIX Presenter"
        self.description = "STIX presenter to export reports into STIX Report format"

    def generate(self, product: dict, template: str | None, parameters: dict[str, str] | None = None) -> str | None:
        report_items = product.get("report_items") or []
        logger.info(f"Sending {len(report_items)} reports to STIX")
        return self.export_to_stix(report_items, product=product)

    def export_to_stix(self, report_items: list[dict] | None, product: dict | None = None) -> str:
        if not report_items:
            logger.warning("No report items provided.")
            return self._create_stix_bundle([])

        stix_objects = self._collect_stix_objects(report_items)
        stix_objects = self._deduplicate_identity_objects(stix_objects)

        report_refs = [obj["id"] for obj in stix_objects if obj.get("type") == "report" and isinstance(obj.get("id"), str)]
        if product_grouping := self._create_product_grouping_object(product, report_refs):
            stix_objects.append(product_grouping)

        return self._create_stix_bundle(stix_objects)

    def _collect_stix_objects(self, report_items: list[dict]) -> list[dict]:
        stix_objects = []
        for report_item in report_items:
            stix_objects.extend(self.convert_to_stix(report_item))
            logger.debug(f"Converted report to STIX: {report_item.get('id')}")
        return stix_objects

    def _deduplicate_identity_objects(self, stix_objects: list[dict]) -> list[dict]:
        deduplicated_objects = []
        seen_identity_ids = set()

        for stix_object in stix_objects:
            if stix_object.get("type") != "identity":
                deduplicated_objects.append(stix_object)
                continue

            object_id = stix_object.get("id")
            if not isinstance(object_id, str):
                deduplicated_objects.append(stix_object)
                continue

            if object_id in seen_identity_ids:
                continue

            seen_identity_ids.add(object_id)
            deduplicated_objects.append(stix_object)

        return deduplicated_objects

    def _create_stix_bundle(self, objects: list[dict]) -> str:
        return json.dumps(
            {
                "type": "bundle",
                "id": f"bundle--{uuid4()}",
                "spec_version": "2.1",
                "objects": objects,
            },
            indent=2,
        )

    def convert_to_stix(self, report_item: dict) -> list[dict]:
        event = MISPEvent()
        base_misp_builder.init_misp_event(event, report_item, sharing_group_id=None, distribution=1)

        event.published = True
        event.publish_timestamp = int(datetime.now(timezone.utc).timestamp())

        for group_title, attributes in report_item.get("attributes", {}).items():
            if not attributes:
                continue

            if report_group_object := self._create_report_group_object(group_title, attributes):
                event.add_object(report_group_object)

        for story in report_item.get("stories", []):
            base_misp_builder.add_story_properties_to_event(deepcopy(story), event)

        parser = MISPtoSTIX21Parser()
        parser.parse_misp_event(event)

        return [json.loads(obj.serialize()) for obj in parser.stix_objects]

    def _create_report_group_object(self, group_title: str, attributes: dict) -> BaseMispObject | None:
        field_entries = []
        for attr_name, attr_value in attributes.items():
            if not attr_name or attr_value in (None, ""):
                continue

            misp_type = TYPE_MAP.get(attr_name, "text")
            if misp_type is None:
                continue

            field_entries.append(json.dumps({"name": attr_name, "type": misp_type, "value": attr_value}, ensure_ascii=False, sort_keys=True))

        if not field_entries:
            return None

        return BaseMispObject(
            parameters={"group_name": group_title, "field": field_entries},
            template="taranis-report-group",
            misp_objects_path_custom=base_misp_builder.DEFAULT_MISP_OBJECTS_PATH,
        )

    def _create_product_grouping_object(self, product: dict | None, report_refs: list[str]) -> dict | None:
        if not product or not report_refs:
            return None

        now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        product_title = str(product.get("title") or "Taranis Product")

        grouping_object = {
            "type": "grouping",
            "spec_version": "2.1",
            "id": f"grouping--{uuid4()}",
            "created": now,
            "modified": now,
            "name": f"Product: {product_title}",
            "context": "unspecified",
            "object_refs": report_refs,
            "x_taranis_product_title": product_title,
            "x_taranis_product_type": str(product.get("type") or ""),
            "x_taranis_product_report_count": len(report_refs),
        }

        if product_description := product.get("description"):
            grouping_object["x_taranis_product_description"] = str(product_description)

        product_id = product.get("id")
        if product_id:
            grouping_object["x_taranis_product_id"] = str(product_id)

        mime_type = product.get("mime_type")
        if mime_type:
            grouping_object["x_taranis_product_mime_type"] = str(mime_type)

        type_id = product.get("type_id", product.get("product_type_id"))
        if type_id is not None:
            grouping_object["x_taranis_product_type_id"] = type_id

        return grouping_object
