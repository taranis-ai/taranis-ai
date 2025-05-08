import json
from datetime import datetime, timezone
from typing import Callable
from pymisp import MISPEventReport, MISPObject, MISPObjectAttribute, MISPShadowAttribute, PyMISP, MISPEvent, MISPAttribute, exceptions

from worker.connectors.definitions.misp_objects import BaseMispObject
from worker.core_api import CoreApi
from worker.log import logger


class MISPConnector:
    def __init__(self):
        self.core_api = CoreApi()
        self.type = "MISP_CONNECTOR"
        self.name = "MISP Connector"
        self.description = "Connector for MISP"

        self.proxies = None
        self.headers = {}
        self.connector_id: str = ""

        self.url: str = ""
        self.api_key: str = ""
        self.org_id: str = ""
        self.ssl: bool = False
        self.request_timeout: int = 5
        self.sharing_group_id: str = ""
        self.distribution: str = "1"

    def parse_parameters(self, parameters: dict) -> None:
        logger.debug(f"{parameters=}")
        self.url = parameters.get("URL", "")
        self.api_key = parameters.get("API_KEY", "")
        self.org_id = parameters.get("ORGANISATION_ID", "")
        self.ssl = parameters.get("SSL", False)
        self.request_timeout = parameters.get("REQUEST_TIMEOUT", 5)
        self.proxies = parameters.get("PROXIES")
        self.headers = parameters.get("HEADERS", {})
        self.sharing_group_id = parameters.get("SHARING_GROUP_ID", "")
        self.distribution = parameters.get("DISTRIBUTION", "")
        if not self.distribution and self.sharing_group_id:
            self.distribution = "4"
        if not self.url or not self.api_key:
            raise ValueError("Missing required parameters")

    def execute(self, connector_config: dict, stories: list) -> None:
        logger.debug(f"{connector_config=}")
        self.parse_parameters(connector_config.get("parameters", ""))
        for story in stories:
            misp_event_uuid = self.get_uuid_if_story_was_shared_to_misp(story)
            self.misp_sender(story, misp_event_uuid)

    def get_uuid_if_story_was_shared_to_misp(self, story: dict) -> str | None:
        story_attributes = story.get("attributes", [])
        return next(
            (attribute.get("value") for attribute in story_attributes if attribute.get("key") == "misp_event_uuid"),
            None,
        )

    @staticmethod
    def get_news_item_object_dict() -> dict:
        """
        Useful for unit testing or ensuring consistent keys.
        If you add or remove a key from here, do the same for the respective object definition file.
        """
        return {
            "author": "",
            "content": "",
            "link": "",
            "published": "",
            "title": "",
            "collected": "",
            "hash": "",
            "id": "",
            "language": "",
            "osint_source_id": "",
            "review": "",
            "source": "",
            "story_id": "",
        }

    @staticmethod
    def get_story_object_dict() -> dict:
        """
        Useful for unit testing or ensuring consistent keys.
        If you add or remove a key from here, do the same for the respective object definition file.
        """
        return {
            "attributes": {},
            "comments": "",
            "created": "",
            "description": "",
            "dislikes": "0",  # TODO: when misp fixes discarding zero value integers, we should use int
            "id": "",
            "important": "",  # TODO: misp is converting bool to int, so we use 0/1 as string
            "likes": "0",  # TODO: when misp fixes discarding zero value integers, we should use int
            "links": {},
            "read": "0",  # TODO: misp is converting bool to int, so we use 0/1 as string
            "relevance": "0",  # TODO: when misp fixes discarding zero value integers, we should use int
            "summary": "",
            "tags": {},
            "title": "",
        }

    def add_news_item_objects(self, news_items: list[dict], event: MISPEvent) -> None:
        """
        For each news item in 'news_items', create a TaranisObject and add it to the event.
        """
        for news_item in news_items:
            news_item.pop("last_change", None)  # key intended for internal use only
            object_data = self.get_news_item_object_dict()
            # sourcery skip: dict-assign-update-to-union
            object_data.update({k: news_item[k] for k in object_data if k in news_item})  # only keep keys that are in the object_data dict

            news_item_object = BaseMispObject(
                parameters=object_data, template="taranis-news-item", misp_objects_path_custom="worker/connectors/definitions/objects"
            )
            event.add_object(news_item_object)

    def add_story_object(self, story: dict, event: MISPEvent) -> None:
        """
        Create a TaranisObject for the story itself, add attributes, links, and tags from the story,
        and attach it to the event with all data correctly stored under their respective keys.
        """
        # Remove internal keys not meant for external processing
        story.pop("last_change", None)

        object_data = self.get_story_object_dict()
        object_data.update({k: story[k] for k in object_data if k in story})
        self._convert_types_to_misp_representation(object_data)
        object_data["attributes"] = []
        object_data["links"] = self._process_items(story, "links", self._process_link)
        object_data["tags"] = self._process_items(story, "tags", self._process_tags)

        story_object = BaseMispObject(
            parameters=object_data,
            template="taranis-story",
            misp_objects_path_custom="worker/connectors/definitions/objects",
        )
        attribute_list = self.add_attributes_from_story(story)
        story_object.add_attributes("attributes", *attribute_list)
        event.add_object(story_object)

    def _convert_types_to_misp_representation(self, object_data) -> None:
        """
        Convert types in the object_data dictionary to MISP representations.
        This step is not necessary but useful in case of comparisons of existing events, because the data comes in that format.
        For example, convert boolean values to integers (0/1).
        """
        object_data["important"] = str(int(object_data.get("important", 0)))
        object_data["read"] = str(int(object_data.get("read", 0)))
        object_data["likes"] = str(object_data.get("likes", 0))
        object_data["dislikes"] = str(object_data.get("dislikes", 0))
        object_data["relevance"] = str(object_data.get("relevance", 0))

    def set_misp_event_uuid_attribute(self, story: dict) -> None:
        """
        Ensure the story has a 'misp_event_uuid' attribute so that the system can determine if it is
        an update or a new event.
        """
        if all(attribute.get("key") != "misp_event_uuid" for attribute in story.get("attributes", [])):
            story.setdefault("attributes", []).append({"key": "misp_event_uuid", "value": f"{story.get('id', '')}"})

    def add_attributes_from_story(self, story: dict) -> list:
        """
        Process attributes from the story, ensuring internal metadata (like misp_event_uuid)
        is added and only valid attributes are included.
        """
        self.set_misp_event_uuid_attribute(story)
        return self._process_items(story, "attributes", self._process_attribute)

    def _process_items(self, story: dict, key: str, processor: Callable) -> list:
        """
        Generic helper to process a list of items stored under the provided key in the story dictionary.

        :param story: The source dictionary containing the items.
        :param key: The key corresponding to the list of items (e.g., 'attributes', 'links', 'tags').
        :param processor: A function that takes an item and returns a processed string (or None if invalid).
        :return: A list of processed item strings.
        """
        items_list = []
        for item in story.get(key, []):
            processed = processor(item)
            if processed is not None:
                items_list.append(processed)
        return items_list

    def _process_attribute(self, attr: dict) -> str | None:
        """
        Process a single attribute dict into its string representation.
        """
        key = attr.get("key", "")
        value = attr.get("value")
        if value is not None:
            attribute_value = f"{{'key': '{key}', 'value': '{value}'}}"
            logger.debug(f"Adding attribute: {attribute_value}")
            return attribute_value
        else:
            logger.warning(f"Skipping attribute with missing value: {attr}")
            return None

    def _process_link(self, link_item: dict) -> str | None:
        """
        Process a single link dict into its string representation.
        """
        link = link_item.get("link", "")
        news_item_id = link_item.get("news_item_id", "")
        if link and news_item_id:
            link_value = f"{{'link': '{link}', 'news_item_id': '{news_item_id}'}}"
            logger.debug(f"Adding link: {link_value}")
            return link_value
        else:
            logger.warning(f"Skipping link with missing data: {link_item}")
            return None

    def _process_tags(self, tag_item: dict) -> str | None:
        """
        Process a single tag dict into its JSON string representation, sanitized.
        """
        name = tag_item.get("name", "")
        tag_type = tag_item.get("tag_type", "")
        if name:
            json_str = json.dumps({"name": name, "tag_type": tag_type})
            logger.debug(f"Adding tag: {json_str}")
            return json_str
        else:
            logger.warning(f"Skipping tag with missing data: {tag_item}")
            return None

    def create_misp_event(self, story: dict) -> MISPEvent:
        """
        Create a MISPEvent from the 'story' dictionary.
        """
        event = MISPEvent()
        event.uuid = story.get("id", "")
        event.info = story.get("title", "")
        event.threat_level_id = 4
        event.analysis = 0
        if self.sharing_group_id:
            event.sharing_group_id = int(self.sharing_group_id)
        if self.distribution:
            event.distribution = int(self.distribution)

        self.add_event_attributes(story, event)
        return event

    def create_event_report_content(self, story) -> str:
        return "# Story description\n" + story.get("description") + "\n\n" + "# Story comment\n" + story.get("comments")

    def create_event_report(self, story: dict, existing_uuid: str | None = None) -> MISPEventReport:
        """
        Creates and returns a MISPEventReport from a story.
        If an existing_uuid is provided, it is reused to allow an update instead of adding a new report.
        """
        report_title = story.get("title", "")
        content = self.create_event_report_content(story)
        new_report = MISPEventReport()
        if existing_uuid:
            new_report.uuid = existing_uuid
        new_report.from_dict(name=report_title, content=content, timestamp=datetime.now(timezone.utc))
        return new_report

    def get_event_by_uuid(self, misp: PyMISP, story: dict, event_uuid: str) -> MISPEvent | None:
        if results := misp.search(controller="events", uuid=event_uuid, pythonify=True):
            logger.debug(f"Event to update exists: {results}")
            return results[0]  # type: ignore
        else:
            logger.error(f"Requested event to update with UUID: {event_uuid} does not exist")
            return None

    def add_event_attributes(self, story: dict, event: MISPEvent) -> None:
        if news_items := story.pop("news_items", None):
            self.add_news_item_objects(news_items, event)
        self.add_story_object(story, event)

    def add_misp_event(self, misp: PyMISP, story: dict) -> MISPEvent | None:
        event = self.create_misp_event(story)
        # Create a new report without reusing any UUID.
        new_report = self.create_event_report(story)
        event.EventReport = [new_report]
        created_event: MISPEvent | dict = misp.add_event(event, pythonify=True)
        return None if isinstance(created_event, dict) else created_event

    def remove_missing_objects_from_misp(self, misp: PyMISP, event: MISPEvent, story: dict) -> None:
        """
        Compare existing MISP objects (with object_relation == 'id') to the IDs in story['news_items'].
        Delete from MISP any object whose ID is no longer in the story.
        """
        current_ids_in_story = {news_item["id"] for news_item in story.get("news_items", []) if "id" in news_item}
        objects_to_remove = []
        for misp_object in event.objects:
            obj_id_value = next(
                (attr.value for attr in misp_object.attributes if attr.object_relation == "id"),
                None,
            )
            if obj_id_value and obj_id_value not in current_ids_in_story:
                objects_to_remove.append(misp_object.id)

        for obj_id in objects_to_remove:
            misp.delete_object(obj_id)
            logger.info(f"Deleted Taranis news object with MISP object ID={obj_id} because its 'id' was removed from the story.")

    def get_event_object_ids(self, event: MISPEvent) -> set:
        ids_in_misp = set()
        for misp_object in event.objects:
            for attr in misp_object.attributes:
                if attr.object_relation == "id":
                    ids_in_misp.add(attr.value)
        return ids_in_misp

    def get_taranis_story_object(self, event: MISPEvent) -> MISPObject | None:
        for obj in event.objects:
            logger.debug(f"{obj=}")
            if obj.name == "taranis-story":
                return obj
        return None

    def drop_existing_news_items(self, story: dict, ids_in_misp: set) -> dict | None:
        """
        Drop news items from 'story' that already exist in the MISP event
        (to avoid adding duplicates).
        """
        if "news_items" in story:
            original_count = len(story["news_items"])
            story["news_items"] = [ni for ni in story["news_items"] if ni.get("id") not in ids_in_misp]
            removed_count = original_count - len(story["news_items"])
            logger.debug(f"Removed {removed_count} news items from 'story' because they exist in MISP.")
            return story
        return None

    def update_misp_event(self, misp: PyMISP, story: dict, misp_event_uuid: str) -> MISPEvent | MISPShadowAttribute | None:
        if event := self.get_event_by_uuid(misp, story, misp_event_uuid):
            event_dict = event.to_dict()
            orgc_id = event_dict.get("orgc_id", None)
            if orgc_id != self.org_id:
                return self._add_proposal_to_event(story, misp_event_uuid, event, misp)

            self.remove_missing_objects_from_misp(misp, event, story)
            ids_in_misp = self.get_event_object_ids(event)
            if story_prepared := self.drop_existing_news_items(story, ids_in_misp):
                return self._update_event(story_prepared, misp_event_uuid, event, misp)
        return None

    def add_proposal(self, existing_event: MISPEvent, event_to_add: MISPEvent, misp: PyMISP) -> MISPShadowAttribute | None:
        existing_object = self.get_taranis_story_object(existing_event)
        new_object = self.get_taranis_story_object(event_to_add)

        if not existing_object or not new_object:
            logger.warning("No Taranis story object found in one of the events.")
            return

        existing_attributes = {attr.object_relation: attr for attr in existing_object.attributes}

        for new_attr in new_object.attributes:
            if new_attr.object_relation in ["links", "tags", "attributes"]:
                logger.info(f"Skipping proposal for {new_attr.object_relation} as it is not supported.")
                continue

            logger.debug(f"Processing new attribute: {new_attr.to_dict()}")
            if not (existing_attr := existing_attributes.get(new_attr.object_relation)):
                logger.error(f"No existing attribute found for {new_attr.object_relation}; cannot add proposal.")
                continue

            if existing_attr.value == new_attr.value:
                logger.info(f"No changes detected for {new_attr.object_relation}. Skipping proposal.")
                continue

            proposal = self._create_proposal(existing_event, existing_object, existing_attr, new_attr)

            try:
                logger.debug(f"Adding proposal for {new_attr.object_relation} with value: {new_attr.value}")
                logger.debug(f"{proposal.to_dict()=}")

                shadow_attribute: MISPShadowAttribute | dict = misp.update_attribute_proposal(existing_attr.id, proposal, pythonify=True)

                if isinstance(shadow_attribute, dict) and "errors" in shadow_attribute:
                    logger.error(f"Failed to add proposal for {new_attr.object_relation}: {shadow_attribute['errors']}")
                    return None
                elif isinstance(shadow_attribute, MISPShadowAttribute):
                    logger.info(f"Proposal successfully added for {new_attr.object_relation}.")
                    return shadow_attribute
            except exceptions.PyMISPError as e:
                logger.error(f"PyMISP error while adding proposal for {new_attr.object_relation}: {e}")
            except Exception as e:
                logger.error(f"Error while adding proposal for {new_attr.object_relation}: {e}")

    def _create_proposal(
        self, existing_event: MISPEvent, existing_object: MISPObject, existing_attr: MISPAttribute, new_attr: MISPObjectAttribute
    ) -> MISPAttribute:
        proposal = MISPAttribute()
        proposal.event_id = existing_event.id
        proposal.object_id = existing_object.id
        proposal.object_relation = new_attr.object_relation
        proposal.value = new_attr.value
        proposal.type = getattr(new_attr, "type", "text")
        # proposal.category = getattr(new_attr, "category", "Other")
        # proposal.to_ids = getattr(new_attr, "to_ids", False)
        proposal.comment = (
            f"Proposed change for {new_attr.object_relation}: "
            f"Current value: {existing_attr.value if existing_attr else 'None'}, "
            f"New value: {new_attr.value}"
        )
        return proposal

    def _update_event(self, story_prepared: dict, misp_event_uuid: str, existing_event: MISPEvent, misp: PyMISP) -> MISPEvent | None:
        event_to_add = self._create_event(story_prepared, misp_event_uuid, existing_event)
        updated_event: MISPEvent | dict = misp.update_event(event_to_add, event_id=existing_event.id, pythonify=True)
        if isinstance(updated_event, dict):
            if "errors" in updated_event:
                error_tuple = updated_event["errors"]
                http_code, error_data = error_tuple[0], error_tuple[1]

                logger.error(f"MISP returned an error. HTTP code: {http_code}. Details: {error_data}")

            logger.error(f"Returned a dict instead of a MISPEvent: {updated_event}")
            return None
        return updated_event

    def _add_proposal_to_event(
        self, story_prepared: dict, misp_event_uuid: str, existing_event: MISPEvent, misp: PyMISP
    ) -> MISPShadowAttribute | None:
        logger.info(
            f"Event with UUID: {misp_event_uuid} is not editable by the organisation with ID: {self.org_id}. A proposal will be attempted instead."
        )
        event_to_add = self._create_event(story_prepared, misp_event_uuid, existing_event)
        shadow_attribute: MISPShadowAttribute | None = self.add_proposal(existing_event, event_to_add, misp)
        logger.debug(f"{shadow_attribute=}")
        return shadow_attribute

    def _create_event(self, story_prepared, misp_event_uuid, existing_event):
        result = self.create_misp_event(story_prepared)
        result.uuid = misp_event_uuid
        existing_report_uuid = None
        if isinstance(existing_event.EventReport, list) and len(existing_event.EventReport) > 0:
            existing_report_uuid = existing_event.EventReport[0].uuid
        new_report = self.create_event_report(story_prepared, existing_report_uuid)
        result.EventReport = [new_report]
        return result

    def send_event_to_misp(self, story: dict, misp_event_uuid: str | None = None) -> MISPEvent | MISPShadowAttribute | None:
        """
        Either update an existing event (if 'misp_event_uuid' is provided)
        or create a new event if no UUID is provided.
        """
        try:
            misp = PyMISP(
                url=self.url,
                key=self.api_key,
                ssl=self.ssl,
                proxies=self.proxies,
                http_headers=self.headers,
            )

            if misp_event_uuid:
                if result := self.update_misp_event(misp, story, misp_event_uuid):
                    logger.info(f"Event with UUID: {result.uuid} was updated in MISP")
                    # TODO: Add validation whether all the objects was fully accepted:
                    # Can happen that an attribute is neglected due to size limitations and we don't know about it.
                    # logger.debug(f"{result.to_dict()=}")
                    # for object in result.objects:
                    #     logger.debug(f"{object.to_dict()=}")

                    return result
                return None

            if created_event := self.add_misp_event(misp, story):
                logger.info(f"Event was created in MISP with UUID: {created_event.uuid}")
                # TODO: Add validation whether all the objects was fully accepted:
                # Can happen that an attribute is neglected due to size limitations and we don't know about it.
                # logger.debug(f"{created_event.to_dict()=}")
                # for object in created_event.objects:
                #     logger.debug(f"{object.to_dict()=}")
                return created_event

            logger.error("Failed to create event in MISP")
            return None

        except exceptions.PyMISPError as e:
            logger.error(f"PyMISP exception occurred, but can be misleading (e.g., if received an HTTP/301 response): {e}")
        except Exception as e:
            logger.error(f"Unexpected error occurred: {e}")
        return None

    def misp_sender(self, story: dict, misp_event_uuid: str | None = None):
        """
        Creates or updates the event in MISP, then updates the story's 'misp_event_uuid' in the backend.
        """
        if result := self.send_event_to_misp(story, misp_event_uuid):
            # Update the Story with the MISP event UUID
            # When an update or create event happened, update the Story so the last_change is set to "external". Don't if it was a proposal.
            if isinstance(result, MISPEvent):
                logger.debug(f"Update the story {story.get('id')} to last_change=external")
                self.core_api.api_post("/worker/stories", story)
                self.core_api.api_patch(
                    f"/bots/story/{story.get('id', '')}/attributes",
                    [{"key": "misp_event_uuid", "value": f"{result.uuid}"}],
                )


def sending():
    connector = MISPConnector()
    connector_config = {
        "description": "",
        "icon": None,
        "id": "b583f4ae-7ec3-492a-a36d-ed9cfc0b4a28",
        "last_attempted": None,
        "last_collected": None,
        "last_error_message": None,
        "name": "https",
        "parameters": {
            "ADDITIONAL_HEADERS": "",
            # "API_KEY": "bXSZEtpNQL6somSCz08x3IzEnDx1bkM6wwZRd0uZ", # org original
            # test@test.com
            "API_KEY": "Q3XI3zQaTQN35Qrx3wvG1iUoQqzwb8m0cd2XcOzK",  # org another one
            "PROXY_SERVER": "",
            "REFRESH_INTERVAL": "",
            "URL": "https://localhost",
            "USER_AGENT": "",
            "SHARING_GROUP_ID": "1",
            "DISTRIBUTION": "",
        },
        "state": -1,
        "type": "misp_connector",
    }
    stories = [
        {
            "comments": "",
            "created": "2024-12-10T07:15:00+01:00",
            "description": 'Adventkalender\nTürchen Nr. 10: Eine kleine Hommage an den Notruf\nDie Weihnachtszeit ist da. Sehen Sie sich täglich das neue Türchen unseres Adventkalenders an und lassen Sie sich von der friedlichen Adventsstimmung verzaubern.\nEine Polizistin und ein Polizist halten Kekse hoch. Sie lächeln, als sie die Zahlen "1-3-3" erkennen – eine kleine Hommage an den Notruf. Die Stimmung und der Duft des frisch gebackenen Gebäcks verbreiteten eine Weihnachtsstimmung. Sie freuen sich auf die besinnliche Zeit, die Momente der Ruhe und des Zusammenhalts inmitten des hektischen Alltags.\nVerfolgen Sie den Adventkalender des Innenministeriums auch auf Facebook und\nInstagram unter "Weiterführende Links".',
            "dislikes": 0,
            "id": "13a3781b-9068-4ae9-a2fa-9da44e4fb230",
            "important": False,
            "likes": 0,
            "links": [],
            "news_items": [
                {
                    "author": "Aktuelles aus dem BM.I",
                    "collected": "2024-12-10T15:37:01.752976+01:00",
                    "content": 'Adventkalender\nTürchen Nr. 10: Eine kleine Hommage an den Notruf\nDie Weihnachtszeit ist da. Sehen Sie sich täglich das neue Türchen unseres Adventkalenders an und lassen Sie sich von der friedlichen Adventsstimmung verzaubern.\nEine Polizistin und ein Polizist halten Kekse hoch. Sie lächeln, als sie die Zahlen "1-3-3" erkennen – eine kleine Hommage an den Notruf. Die Stimmung und der Duft des frisch gebackenen Gebäcks verbreiteten eine Weihnachtsstimmung. Sie freuen sich auf die besinnliche Zeit, die Momente der Ruhe und des Zusammenhalts inmitten des hektischen Alltags.\nVerfolgen Sie den Adventkalender des Innenministeriums auch auf Facebook und\nInstagram unter "Weiterführende Links".',
                    "hash": "be225cdb83c8ab06528af22eabfc28942e272e54694d5f9f5b18ea80993fa580",
                    "id": "335d2d0d-e824-443d-ba8a-68e787b4b3b0",
                    "language": "",
                    "link": "https://www.bmi.gv.at/news.aspx?id=4D737532623078435875493D",
                    "osint_source_id": "9b243209-19ad-4f90-9a7f-b6e957c867c1",
                    "published": "2024-12-10T07:15:00+01:00",
                    "review": "",
                    "source": "https://www.bmi.gv.at/rss/bmi_presse.xml",
                    "story_id": "13a3781b-9068-4ae9-a2fa-9da44e4fb230",
                    "title": "Türchen Nr. 10: Eine kleine Hommage an den Notruf",
                    "updated": "2024-12-10T15:37:01.173551+01:00",
                }
            ],
            "read": False,
            "relevance": 0,
            "summary": "",
            "tags": {},
            "title": "Türchen Nr. 10: Eine kleine Hommage an den Notruf",
            "updated": "2024-12-10T15:37:46.641183+01:00",
        }
    ]
    connector.execute(connector_config, stories)


if __name__ == "__main__":
    sending()
