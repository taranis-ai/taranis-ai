import contextlib
from datetime import datetime, timezone

from pymisp import MISPAttribute, MISPEvent, MISPEventReport, MISPObject, MISPObjectAttribute, MISPShadowAttribute, PyMISP, exceptions

from worker.connectors import base_misp_builder
from worker.connectors.definitions.misp_objects import BaseMispObject
from worker.core_api import CoreApi
from worker.log import logger


class MispConnector:
    def __init__(self):
        self.type = "MISP_CONNECTOR"
        self.name = "MISP Connector"
        self.description = "Connector for MISP"
        self.core_api = CoreApi()

        self.proxies = None
        self.headers = {}
        self.connector_id: str = ""

        self.url: str = ""
        self.api_key: str = ""
        self.org_id: str = ""
        self.ssl: bool = False
        self.request_timeout: int = 5
        self.sharing_group_id: int | None = None
        self.distribution: int | None = None

    def parse_parameters(self, parameters: dict) -> None:
        self.url = parameters.get("URL", "")
        self.api_key = parameters.get("API_KEY", "")
        self.org_id = parameters.get("ORGANISATION_ID", "")
        self.ssl = parameters.get("SSL", False)
        self.request_timeout = parameters.get("REQUEST_TIMEOUT", 5)
        self.proxies = parameters.get("PROXIES")
        self.headers = parameters.get("HEADERS", {})
        try:
            self.sharing_group_id = int(parameters.get("SHARING_GROUP_ID", "")) if parameters.get("SHARING_GROUP_ID") else None
        except ValueError:
            logger.warning(f"Invalid SHARING_GROUP_ID value: {parameters.get('SHARING_GROUP_ID')}. Setting to None.")
            self.sharing_group_id = None

        self.distribution = self._parse_distribution(parameters.get("DISTRIBUTION", ""))
        if not self.url or not self.api_key:
            raise ValueError("Missing required parameters")

    def _parse_distribution(self, raw_distribution: str | None) -> int:
        if not raw_distribution:
            raw_distribution = "4" if self.sharing_group_id else "0"
        try:
            return int(raw_distribution)
        except ValueError:
            logger.warning(f"Invalid DISTRIBUTION value: {raw_distribution}. Falling back to 0.")
            return 0

    def execute(self, connector_data: dict) -> None:
        connector_config = connector_data.get("connector_config")
        stories = connector_data.get("story", [])
        if connector_config is None:
            logger.error("A MISP Connector has not been found")
            return None
        self.parse_parameters(connector_config.get("parameters", ""))
        for story in stories:
            misp_event_uuid = self.get_uuid_if_story_was_shared_to_misp(story)
            self.misp_sender(story, misp_event_uuid)

    def get_uuid_if_story_was_shared_to_misp(self, story: dict) -> str | None:
        story_attributes: dict = story.get("attributes", {})
        return next(
            (
                value_dict.get("value")
                for key, value_dict in story_attributes.items()
                if isinstance(value_dict, dict) and key == "misp_event_uuid"
            ),
            None,
        )

    def add_news_item_objects(self, news_items: list[dict], event: MISPEvent) -> None:
        """
        For each news item in 'news_items', create a TaranisObject and add it to the event.
        """
        for news_item in news_items:
            news_item.pop("last_change", None)  # key intended for internal use only
            object_data = base_misp_builder.get_news_item_object_dict_empty()
            # sourcery skip: dict-assign-update-to-union
            object_data.update({k: news_item[k] for k in object_data if k in news_item})  # only keep keys that are in the object_data dict

            news_item_object = BaseMispObject(
                parameters=object_data, template="taranis-news-item", misp_objects_path_custom="worker/connectors/definitions/objects"
            )
            event.add_object(news_item_object)

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

    def add_story_properties_to_event(self, story: dict, event: MISPEvent) -> None:
        if news_items := story.pop("news_items", None):
            self.add_news_item_objects(news_items, event)
        base_misp_builder.add_story_object(story, event)

    def add_misp_event(self, misp: PyMISP, story: dict) -> MISPEvent | None:
        event = MISPEvent()
        base_misp_builder.init_misp_event(event, story, self.sharing_group_id, self.distribution)
        self.add_story_properties_to_event(story, event)

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

    def get_taranis_news_item_object_hash_list(self, event: MISPEvent) -> list[str] | None:
        news_item_obj_hash_list = []
        for obj in event.objects:
            if obj.name == "taranis-news-item":
                news_item_obj_hash_list.extend(attr.value for attr in obj.attributes if attr.object_relation == "hash")
        return news_item_obj_hash_list or None

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

    def update_misp_event(self, misp: PyMISP, story: dict, misp_event_uuid: str) -> MISPEvent | list[MISPShadowAttribute] | None:
        if event := self.get_event_by_uuid(misp, story, misp_event_uuid):
            event_dict = event.to_dict()
            orgc_id = event_dict.get("orgc_id", None)

            if orgc_id != self.org_id:
                extension_id = self.add_missing_news_items_as_extension(event, story, misp)
                self.propose_removal_of_old_news_items_with_attribute_proposals(event, story, misp, extension_id)

                if shadow_attributes := self._add_attribute_proposal_to_event(story, misp_event_uuid, event, misp):
                    logger.info(f"{len(shadow_attributes)} attribute proposals submitted.")
                    return shadow_attributes
                else:
                    logger.warning("No attribute proposals were submitted.")
                    return None

            self.remove_missing_objects_from_misp(misp, event, story)
            ids_in_misp = self.get_event_object_ids(event)
            if story_prepared := self.drop_existing_news_items(story, ids_in_misp):
                return self._update_event(story_prepared, misp_event_uuid, event, misp)
        return None

    def add_story_proposal(self, existing_event: MISPEvent, event_to_add: MISPEvent, misp: PyMISP) -> list[MISPShadowAttribute]:
        existing_object = self.get_taranis_story_object(existing_event)
        new_object = self.get_taranis_story_object(event_to_add)

        if not existing_object or not new_object:
            logger.warning(f"No Taranis story object found in event {existing_event.id}")
            return []

        existing_attributes = {attr.object_relation: attr for attr in existing_object.attributes}
        shadow_attributes: list[MISPShadowAttribute] = []

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

            attribute_proposal = self._create_attribute_proposal(existing_event, existing_object, existing_attr, new_attr)

            try:
                logger.debug(f"Adding proposal for {new_attr.object_relation} with value: {new_attr.value}")
                logger.debug(f"{attribute_proposal.to_dict()=}")

                shadow_attribute = misp.update_attribute_proposal(existing_attr.id, attribute_proposal, pythonify=True)

                if isinstance(shadow_attribute, dict) and "errors" in shadow_attribute:
                    logger.error(f"Failed to add proposal for {new_attr.object_relation}: {shadow_attribute['errors']}")
                elif isinstance(shadow_attribute, MISPShadowAttribute):
                    logger.info(f"Proposal successfully added for {new_attr.object_relation}.")
                    shadow_attributes.append(shadow_attribute)

            except exceptions.PyMISPError as e:
                logger.error(f"PyMISP error while adding proposal for {new_attr.object_relation}: {e}")
            except Exception as e:
                logger.error(f"Error while adding proposal for {new_attr.object_relation}: {e}")

        return shadow_attributes

    def _get_parent_hashes(self, existing_event: MISPEvent) -> set[str]:
        return set(self.get_taranis_news_item_object_hash_list(existing_event) or [])

    def _get_incoming_hashes(self, story: dict) -> set[str]:
        items = story.get("news_items", []) or []
        return {ni.get("hash") for ni in items if ni.get("hash")}

    def _get_hashes_to_remove(self, extension_event: MISPEvent, incoming_hashes: set[str]) -> list[tuple[str, int]]:
        to_remove = []
        for obj in extension_event.objects:
            if obj.name != "taranis-news-item":
                continue
            obj_hash = next((attr.value for attr in obj.attributes if attr.object_relation == "hash"), None)
            if obj_hash and obj_hash not in incoming_hashes:
                to_remove.append((obj_hash, obj.id))
        return to_remove

    def _get_hashes_to_add(self, parent_hashes: set[str], extension_hashes: set[str], incoming_hashes: set[str]) -> list[str]:
        return [h for h in incoming_hashes if h not in parent_hashes and h not in extension_hashes]

    def _create_extension_event(self, existing_event: MISPEvent, hashes_to_add: list[str], misp: PyMISP) -> MISPEvent | None:
        new_event = MISPEvent()
        new_event.info = f"Extension of Event {existing_event.id} – new news items added"
        new_event.distribution = existing_event.distribution
        new_event.threat_level_id = existing_event.threat_level_id
        new_event.analysis = existing_event.analysis
        new_event.extends_uuid = existing_event.uuid
        if self.sharing_group_id:
            new_event.sharing_group_id = self.sharing_group_id
        try:
            created = misp.add_event(new_event, pythonify=True)
            return None if isinstance(created, dict) and created.get("errors") else created  # type: ignore
        except exceptions.PyMISPError:
            return None

    def _delete_stale_objects(self, hashes_to_remove: list[tuple[str, int]], misp: PyMISP) -> None:
        for _, obj_id in hashes_to_remove:
            with contextlib.suppress(Exception):
                misp.delete_object(obj_id)

    def _add_new_objects(self, extension_event_id: int, incoming_items: list[dict], hashes_to_add: list[str], misp: PyMISP) -> None:
        hash_to_obj: dict[str, MISPObject] = {}
        for ni in incoming_items:
            h = ni.get("hash")
            if not h or h not in hashes_to_add:
                continue
            data = base_misp_builder.get_news_item_object_dict_empty()
            data.update({k: ni[k] for k in data if k in ni})
            base_obj = BaseMispObject(
                parameters=data, template="taranis-news-item", misp_objects_path_custom="worker/connectors/definitions/objects"
            )
            hash_to_obj[h] = base_obj
        for h in hashes_to_add:
            obj_to_add = hash_to_obj.get(h)
            if not obj_to_add:
                continue
            with contextlib.suppress(Exception):
                misp.add_object(extension_event_id, obj_to_add)

    def add_missing_news_items_as_extension(
        self,
        existing_event: MISPEvent,
        story: dict,
        misp: PyMISP,
    ) -> int | None:
        parent_hashes = self._get_parent_hashes(existing_event)
        extension_event = self._find_existing_extension_by_org(misp, existing_event)
        if extension_event:
            extension_hashes = set(self.get_taranis_news_item_object_hash_list(extension_event) or [])
        else:
            extension_hashes = set()
        incoming_items = story.get("news_items", []) or []
        incoming_hashes = self._get_incoming_hashes(story)
        hashes_to_remove = self._get_hashes_to_remove(extension_event, incoming_hashes) if extension_event else []
        hashes_to_add = self._get_hashes_to_add(parent_hashes, extension_hashes, incoming_hashes)
        if not hashes_to_remove and not hashes_to_add:
            return None
        if not extension_event:
            extension_event = self._create_extension_event(existing_event, hashes_to_add, misp)
        if not extension_event:
            return None
        extension_event_id = extension_event.id  # type: ignore
        self._delete_stale_objects(hashes_to_remove, misp)
        self._add_new_objects(extension_event_id, incoming_items, hashes_to_add, misp)
        return extension_event_id

    def _find_existing_extension_by_org(self, misp: PyMISP, parent_event: MISPEvent) -> MISPEvent | None:
        # sourcery skip: use-next
        """
        Work around the non‐working 'extends_uuid' filter by retrieving a
        reasonable subset of recent events and then returning the first one
        whose .extends_uuid == parent_event.uuid and .org_id == self.org_id.
        """
        try:
            parent_ts = parent_event.timestamp
            candidates = misp.search(controller="events", date_from=parent_ts, pythonify=True)
        except exceptions.PyMISPError as e:
            logger.error(f"Error fetching candidate events for extension search: {e}")
            return None

        for ev in candidates:
            if getattr(ev, "extends_uuid", None) == parent_event.uuid and str(ev.org_id) == str(self.org_id):  # type: ignore
                return ev  # type: ignore

        return None

    def _check_news_item_to_remove(self, existing_news_item_hash_list: list, new_news_item_hash_list: list) -> list | None:
        news_item_hash_to_remove = []
        for existing_hash in existing_news_item_hash_list:
            if existing_hash not in new_news_item_hash_list:
                logger.debug(f"News item will be proposed to remove: {existing_hash}")
                news_item_hash_to_remove.append(existing_hash)

        return news_item_hash_to_remove or None

    def propose_removal_of_old_news_items_with_attribute_proposals(
        self,
        existing_event: MISPEvent,
        story: dict,
        misp: PyMISP,
        extension_event_id: int | None = None,
    ) -> None:
        """
        1) Build two lists of hashes: one from existing_event, one from story['news_items'].
        2) Call _check_news_item_to_remove(...) to see which existing hashes no longer appear.
        3) For each hash-to-remove:
            a) Find the matching MISPObject (name == "taranis-news-item") in existing_event.
            b) Within that object, locate the Attribute whose object_relation == "hash".
            c) Build a MISPAttribute proposal via _create_attribute_proposal, then override the comment.
            d) Call misp.update_attribute_proposal(orig_attribute_id, proposal).
        4) If extension_event_id is given, the comment will reference it; otherwise use the "no extension" fallback.
        """

        existing_hashes = self.get_taranis_news_item_object_hash_list(existing_event) or []

        new_items = story.get("news_items", []) or []
        new_hashes = [ni.get("hash") for ni in new_items if ni.get("hash")]

        hashes_to_remove = self._check_news_item_to_remove(existing_hashes, new_hashes)
        if not hashes_to_remove:
            logger.info("No news‐item hashes to propose for removal.")
            return

        for h in hashes_to_remove:
            found_obj = None
            found_attr = None

            for misp_obj in existing_event.objects:
                if misp_obj.name != "taranis-news-item":
                    continue

                for attr in misp_obj.attributes:
                    if attr.object_relation == "hash" and attr.value == h:
                        found_obj = misp_obj
                        found_attr = attr
                        break

                if found_obj:
                    break

            if not found_obj or not found_attr:
                logger.error(f"Could not locate MISPObject or its 'hash' attribute for hash='{h}'; skipping proposal.")
                continue

            proposal = self._create_attribute_proposal(
                existing_event,
                found_obj,
                found_attr,
                new_attr=found_attr,
            )

            if extension_event_id is not None:
                proposal.comment = (
                    f"This news‐item can be removed. Please review the new items in extension Event "
                    f"{extension_event_id} and consider adding any relevant items from there."
                )
            else:
                proposal.comment = (
                    "This news‐item is not considered a good fit for the story. Please consider deletion and update of this event."
                )

            try:
                shadow_attr = misp.update_attribute_proposal(found_attr.id, proposal, pythonify=True)
                if isinstance(shadow_attr, dict) and shadow_attr.get("errors"):
                    logger.error(f"Failed to propose update on attribute (hash={h}, attr_id={found_attr.id}): {shadow_attr['errors']}")
                else:
                    logger.info(f"Proposed attribute update on news‐item (hash={h}, attr_id={found_attr.id}).")
            except exceptions.PyMISPError as e:
                logger.error(f"PyMISP error while proposing attribute update for hash={h}, attr_id={found_attr.id}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error while proposing attribute update for hash={h}, attr_id={found_attr.id}: {e}")

    def _create_attribute_proposal(
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

    def _add_attribute_proposal_to_event(
        self, story_prepared: dict, misp_event_uuid: str, existing_event: MISPEvent, misp: PyMISP
    ) -> list[MISPShadowAttribute]:
        logger.info(
            f"Event with UUID: {misp_event_uuid} is not editable by the organisation with ID: {self.org_id}. A proposal will be attempted instead."
        )
        event_to_add = self._create_event(story_prepared, misp_event_uuid, existing_event)
        shadow_attributes = self.add_story_proposal(existing_event, event_to_add, misp)
        logger.debug(f"Proposed attributes (shadow attributes): {shadow_attributes=}")
        return shadow_attributes

    def _create_event(self, story_prepared, misp_event_uuid, existing_event) -> MISPEvent:
        event = MISPEvent()
        base_misp_builder.init_misp_event(event, story_prepared, self.sharing_group_id, self.distribution)
        self.add_story_properties_to_event(story_prepared, event)

        event.uuid = misp_event_uuid
        existing_report_uuid = None
        if isinstance(existing_event.EventReport, list) and len(existing_event.EventReport) > 0:
            existing_report_uuid = existing_event.EventReport[0].uuid
        new_report = self.create_event_report(story_prepared, existing_report_uuid)
        event.EventReport = [new_report]
        return event

    def send_event_to_misp(self, story: dict, misp_event_uuid: str | None = None) -> MISPEvent | list[MISPShadowAttribute] | None:
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
                    if isinstance(result, MISPEvent):
                        logger.info(f"Event with UUID: {result.uuid} was updated in MISP")
                    elif isinstance(result, list) and all(isinstance(x, MISPShadowAttribute) for x in result):
                        logger.info(f"{len(result)} attribute proposals submitted for non-editable event {misp_event_uuid}")
                    else:
                        logger.warning(f"Unexpected return type from update_misp_event: {type(result)}")

                    return result

                logger.warning(f"Failed to update event with UUID: {misp_event_uuid}")
                return None

            if created_event := self.add_misp_event(misp, story):
                logger.info(f"Event was created in MISP with UUID: {created_event.uuid}")
                return created_event

            logger.error("Failed to create event in MISP")
            return None

        except exceptions.PyMISPError as e:
            logger.error(f"PyMISP exception occurred, possibly due to HTTP/301 or SSL issues: {e}")
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
                self._set_last_change_external(story)
                self.core_api.api_patch(
                    f"/bots/story/{story.get('id', '')}/attributes",
                    {"misp_event_uuid": {"key": "misp_event_uuid", "value": f"{result.uuid}"}},
                )

    def _set_last_change_external(self, story: dict):
        story_changes: dict[str, str] = {story.get("id", ""): "external"}

        news_item_changes: dict[str, str] = {
            item.get("id", ""): "external" for item in story.get("news_items", []) if item.get("last_change") == "internal"
        }

        payload: dict[str, dict[str, str]] = {
            "stories": story_changes,
            "news_items": news_item_changes,
        }
        self.core_api.api_put("/worker/misp/last-change", payload)
