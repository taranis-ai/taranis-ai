import base64
import copy
import json
import os
import uuid
from io import BytesIO

from PIL import Image
from werkzeug.datastructures import FileStorage

from core.config import Config
from tests.functional.helpers import BaseTest


_INVALID_IMAGE_BYTES = b"not-an-image"
_INVALID_IMAGE_BASE64 = base64.b64encode(_INVALID_IMAGE_BYTES).decode("utf-8")


def _make_icon_base64(size: tuple[int, int], image_format: str, mode: str = "RGBA", color=(80, 140, 220, 255)) -> str:
    image = Image.new(mode, size, color)
    if image_format == "JPEG" and image.mode != "RGB":
        image = image.convert("RGB")
    with BytesIO() as output:
        image.save(output, format=image_format)
        return base64.b64encode(output.getvalue()).decode("utf-8")


_VALID_JPEG_ICON_BASE64 = _make_icon_base64((24, 12), "JPEG", mode="RGB", color=(80, 140, 220))
_VALID_WIDE_PNG_ICON_BASE64 = _make_icon_base64((Config.OSINT_SOURCE_ICON_PIXELS, Config.OSINT_SOURCE_ICON_PIXELS // 2), "PNG")


class TestSourcesConfigApi(BaseTest):
    base_uri = "/api/config"

    @staticmethod
    def _assert_normalized_icon(icon_base64: str) -> None:
        icon_bytes = base64.b64decode(icon_base64)
        with Image.open(BytesIO(icon_bytes)) as image:
            assert image.format == "PNG"
            assert image.size == (Config.OSINT_SOURCE_ICON_PIXELS, Config.OSINT_SOURCE_ICON_PIXELS)

    def test_import_osint_sources(self, client, auth_header, cleanup_sources):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        file_path = os.path.join(dir_path, "osint_sources_test_data_v1.json")
        with open(file_path, "rb") as f:
            file_storage = FileStorage(stream=f, filename="osint_sources_test_data_v1.json", content_type="application/json")
            data = {"file": file_storage}
            response = self.assert_post_data_ok(client, uri="import-osint-sources", data=data, auth_header=auth_header)
            assert response.json["count"] == 6
            assert response.json["message"] == "Successfully imported sources"

    def test_import_osint_sources_v3_defaults_rank_to_zero(self, client, auth_header):
        payload = {
            "version": 3,
            "sources": [
                {
                    "name": "V3 Import Source",
                    "description": "",
                    "type": "rss_collector",
                    "parameters": [{"FEED_URL": "https://example.com/v3.xml"}],
                }
            ],
        }

        response = self.assert_post_ok(client, uri="import-osint-sources", json_data=payload, auth_header=auth_header)
        source_id = response.json["sources"][0]

        try:
            source_response = self.assert_get_ok(client, uri=f"osint-sources/{source_id}", auth_header=auth_header)
            assert source_response.json["rank"] == 0
        finally:
            client.delete(self.concat_url(f"osint-sources/{source_id}"), headers=auth_header)

    def test_import_osint_sources_v4_keeps_rank(self, client, auth_header):
        payload = {
            "version": 4,
            "sources": [
                {
                    "name": "V4 Import Source",
                    "description": "",
                    "rank": 5,
                    "type": "rss_collector",
                    "parameters": {"FEED_URL": "https://example.com/v4.xml"},
                }
            ],
        }

        response = self.assert_post_ok(client, uri="import-osint-sources", json_data=payload, auth_header=auth_header)
        source_id = response.json["sources"][0]

        try:
            source_response = self.assert_get_ok(client, uri=f"osint-sources/{source_id}", auth_header=auth_header)
            assert source_response.json["rank"] == 5
        finally:
            client.delete(self.concat_url(f"osint-sources/{source_id}"), headers=auth_header)

    def test_export_osint_sources(self, client, auth_header, cleanup_sources):
        response = self.assert_get_ok(client, uri="export-osint-sources", auth_header=auth_header)
        dir_path = os.path.dirname(os.path.realpath(__file__))
        file_path = os.path.join(dir_path, "osint_sources_test_data_v4.json")
        with open(file_path, "rb") as f:
            test_data = json.load(f)
            test_result = response.json
            assert test_result["version"] == 4
            for source in test_data["data"]:
                assert source in test_result["sources"]

    def test_create_source(self, client, auth_header, cleanup_sources):
        response = self.assert_post_ok(client, uri="osint-sources", json_data=cleanup_sources, auth_header=auth_header)
        assert response.json["message"] == "OSINT source created successfully"
        assert response.json["id"] == cleanup_sources["id"]

        source_response = self.assert_get_ok(client, uri=f"osint-sources/{cleanup_sources['id']}", auth_header=auth_header)
        assert source_response.json["rank"] == 0

    def test_create_and_modify_source_normalizes_icon(self, client, auth_header, cleanup_sources):
        source_payload = copy.deepcopy(cleanup_sources)
        source_id = uuid.uuid4().hex
        source_payload["id"] = source_id
        source_payload["icon"] = _VALID_JPEG_ICON_BASE64

        create_response = client.post(self.concat_url("osint-sources"), json=source_payload, headers=auth_header)
        assert create_response.status_code == 201

        try:
            source_response = self.assert_get_ok(client, uri=f"osint-sources/{source_id}", auth_header=auth_header)
            self._assert_normalized_icon(source_response.json["icon"])

            update_response = self.assert_put_ok(
                client,
                uri=f"osint-sources/{source_id}",
                json_data={"icon": _VALID_WIDE_PNG_ICON_BASE64},
                auth_header=auth_header,
            )
            assert update_response.json["id"] == source_id

            updated_source_response = self.assert_get_ok(client, uri=f"osint-sources/{source_id}", auth_header=auth_header)
            self._assert_normalized_icon(updated_source_response.json["icon"])
        finally:
            client.delete(self.concat_url(f"osint-sources/{source_id}"), headers=auth_header)

    def test_create_source_rejects_invalid_icon(self, client, auth_header, cleanup_sources):
        source_payload = copy.deepcopy(cleanup_sources)
        source_payload["id"] = uuid.uuid4().hex
        source_payload["icon"] = _INVALID_IMAGE_BASE64

        response = client.post(self.concat_url("osint-sources"), json=source_payload, headers=auth_header)

        assert response.status_code == 400
        assert response.json["error"] == "Icon payload is not a valid image file."

    def test_create_source_rejects_invalid_rank(self, client, auth_header, cleanup_sources):
        source_payload = copy.deepcopy(cleanup_sources)
        source_payload["id"] = uuid.uuid4().hex
        source_payload["rank"] = 6

        response = client.post(self.concat_url("osint-sources"), json=source_payload, headers=auth_header)

        assert response.status_code == 400
        assert "Validation failed for model 'OSINTSource':" in response.json["error"]
        assert "Field 'rank': Input should be less than or equal to 5" in response.json["error"]

    def test_modify_source(self, client, auth_header, cleanup_sources):
        source_data = {
            "description": "Sourcy McSourceFace",
            "rank": 5,
        }
        source_id = cleanup_sources["id"]
        response = self.assert_put_ok(client, uri=f"osint-sources/{source_id}", json_data=source_data, auth_header=auth_header)
        assert response.json["id"] == f"{source_id}"

        source_response = self.assert_get_ok(client, uri=f"osint-sources/{source_id}", auth_header=auth_header)
        assert source_response.json["description"] == "Sourcy McSourceFace"
        assert source_response.json["rank"] == 5

    def test_modify_source_can_store_rank_zero(self, client, auth_header, cleanup_sources):
        source_id = cleanup_sources["id"]
        response = self.assert_put_ok(client, uri=f"osint-sources/{source_id}", json_data={"rank": 0}, auth_header=auth_header)
        assert response.json["id"] == f"{source_id}"

        source_response = self.assert_get_ok(client, uri=f"osint-sources/{source_id}", auth_header=auth_header)
        assert source_response.json["rank"] == 0

    def test_modify_source_rejects_invalid_icon(self, client, auth_header, cleanup_sources):
        source_payload = copy.deepcopy(cleanup_sources)
        source_id = uuid.uuid4().hex
        source_payload["id"] = source_id

        create_response = client.post(self.concat_url("osint-sources"), json=source_payload, headers=auth_header)
        assert create_response.status_code == 201

        try:
            response = client.put(
                self.concat_url(f"osint-sources/{source_id}"),
                json={"icon": _INVALID_IMAGE_BASE64},
                headers=auth_header,
            )

            assert response.status_code == 400
            assert response.json["error"] == "Icon payload is not a valid image file."
        finally:
            client.delete(self.concat_url(f"osint-sources/{source_id}"), headers=auth_header)

    def test_get_sources(self, client, auth_header, cleanup_sources):
        source_id = cleanup_sources["id"]
        response = self.assert_get_ok(client, uri=f"osint-sources?search={cleanup_sources['name']}", auth_header=auth_header)
        assert response.json["total_count"] == 1
        assert response.json["items"][0]["name"] == cleanup_sources["name"]
        assert response.json["items"][0]["description"] == "Sourcy McSourceFace"
        assert response.json["items"][0]["id"] == source_id
        assert response.json["items"][0]["rank"] == 0

    def test_get_sources_excludes_manual_collectors_by_default(self, client, auth_header, app):
        from core.model.osint_source import OSINTSource

        unique_suffix = uuid.uuid4().hex
        rss_source_id = f"rss-{unique_suffix}"
        manual_source_id = f"manual-{unique_suffix}"

        rss_source = {
            "id": rss_source_id,
            "name": f"Visible Source {unique_suffix}",
            "description": "Collector that should remain visible",
            "parameters": {"FEED_URL": "https://example.invalid/feed.xml"},
            "type": "rss_collector",
        }
        manual_source = {
            "id": manual_source_id,
            "name": f"Visible Source {unique_suffix}",
            "description": "Collector that should be hidden by default",
            "parameters": {},
            "type": "manual_collector",
        }

        with app.app_context():
            OSINTSource.add(rss_source)
            OSINTSource.add(manual_source)

        try:
            response = self.assert_get_ok(client, uri=f"osint-sources?search={unique_suffix}&fetch_all=true", auth_header=auth_header)
            payload = response.get_json()

            assert payload["total_count"] == 1
            assert [item["id"] for item in payload["items"]] == [rss_source_id]
        finally:
            with app.app_context():
                if OSINTSource.get(rss_source_id):
                    OSINTSource.delete(rss_source_id)
                if OSINTSource.get(manual_source_id):
                    OSINTSource.delete(manual_source_id)

    def test_get_sources_orders_by_status(self, client, auth_header, app):
        from core.model.osint_source import OSINTSource
        from core.model.task import Task

        unique_suffix = uuid.uuid4().hex
        failure_source_id = f"failure-{unique_suffix}"
        success_source_id = f"success-{unique_suffix}"

        sources = [
            {
                "id": failure_source_id,
                "name": f"Status Ordered Source {unique_suffix}",
                "description": "Failure source",
                "parameters": {"FEED_URL": "https://example.invalid/failure.xml"},
                "type": "rss_collector",
            },
            {
                "id": success_source_id,
                "name": f"Status Ordered Source {unique_suffix}",
                "description": "Success source",
                "parameters": {"FEED_URL": "https://example.invalid/success.xml"},
                "type": "rss_collector",
            },
        ]
        tasks = [
            {"id": f"collect_rss_collector_{failure_source_id}", "task": "collector_task", "status": "FAILURE"},
            {"id": f"collect_rss_collector_{success_source_id}", "task": "collector_task", "status": "SUCCESS"},
        ]

        with app.app_context():
            for source in sources:
                OSINTSource.add(source)
            for task in tasks:
                Task.add(task)

        try:
            asc_response = self.assert_get_ok(
                client,
                uri=f"osint-sources?search={unique_suffix}&order=status_asc&fetch_all=true",
                auth_header=auth_header,
            )
            asc_payload = asc_response.get_json()
            assert asc_payload["total_count"] == 2
            assert [item["id"] for item in asc_payload["items"]] == [failure_source_id, success_source_id]

            desc_response = self.assert_get_ok(
                client,
                uri=f"osint-sources?search={unique_suffix}&order=status_desc&fetch_all=true",
                auth_header=auth_header,
            )
            desc_payload = desc_response.get_json()
            assert desc_payload["total_count"] == 2
            assert [item["id"] for item in desc_payload["items"]] == [success_source_id, failure_source_id]
        finally:
            with app.app_context():
                for task in tasks:
                    if Task.get(task["id"]):
                        Task.delete(task["id"])
                for source in sources:
                    if OSINTSource.get(source["id"]):
                        OSINTSource.delete(source["id"])

    def test_delete_source(self, client, auth_header, cleanup_sources):
        source_id = cleanup_sources["id"]
        response = self.assert_delete_ok(client, uri=f"osint-sources/{source_id}", auth_header=auth_header)
        assert response.json["message"] == "OSINT Source Test Source deleted"

    def test_create_source_group(self, client, auth_header, cleanup_source_groups):
        response = self.assert_post_ok(client, uri="osint-source-groups", json_data=cleanup_source_groups, auth_header=auth_header)
        assert response.json["message"] == "OSINT source group created successfully"
        assert response.json["id"] == cleanup_source_groups["id"]

    def test_modify_source_group(self, client, auth_header, cleanup_source_groups):
        source_group_data = {
            "name": cleanup_source_groups["name"],
            "description": "Groupy McGroupFace",
        }
        source_group_id = cleanup_source_groups["id"]
        response = self.assert_put_ok(
            client, uri=f"osint-source-groups/{source_group_id}", json_data=source_group_data, auth_header=auth_header
        )
        assert response.json["id"] == f"{source_group_id}"

    def test_get_source_groups(self, client, auth_header, cleanup_source_groups):
        source_group_id = cleanup_source_groups["id"]
        response = self.assert_get_ok(client, uri=f"osint-source-groups?search={cleanup_source_groups['name']}", auth_header=auth_header)
        assert response.json["total_count"] == 1
        assert response.json["items"][0]["name"] == cleanup_source_groups["name"]
        assert response.json["items"][0]["description"] == "Groupy McGroupFace"
        assert response.json["items"][0]["id"] == source_group_id

    def test_delete_source_group(self, client, auth_header, cleanup_source_groups):
        source_group_id = cleanup_source_groups["id"]
        response = self.assert_delete_ok(client, uri=f"osint-source-groups/{source_group_id}", auth_header=auth_header)
        assert response.json["message"] == f"Successfully deleted {source_group_id}"


class TestWorkerSourceIcon(BaseTest):
    base_uri = "/api/worker"

    def test_worker_icon_upload_rejects_invalid_image(self, client, auth_header, api_header, cleanup_sources):
        source_payload = copy.deepcopy(cleanup_sources)
        source_id = uuid.uuid4().hex
        source_payload["id"] = source_id

        create_response = client.post("/api/config/osint-sources", json=source_payload, headers=auth_header)
        assert create_response.status_code == 201

        try:
            upload_headers = dict(api_header)
            upload_headers.pop("Content-type", None)

            response = client.put(
                self.concat_url(f"osint-sources/{source_id}/icon"),
                data={"file": (BytesIO(_INVALID_IMAGE_BYTES), "icon.png")},
                headers=upload_headers,
                content_type="multipart/form-data",
            )

            assert response.status_code == 400
            assert response.json["error"] == "Icon payload is not a valid image file."
        finally:
            client.delete(f"/api/config/osint-sources/{source_id}", headers=auth_header)

    def test_worker_icon_upload_requires_api_key(self, client, auth_header, cleanup_sources):
        source_payload = copy.deepcopy(cleanup_sources)
        source_id = uuid.uuid4().hex
        source_payload["id"] = source_id

        create_response = client.post("/api/config/osint-sources", json=source_payload, headers=auth_header)
        assert create_response.status_code == 201

        try:
            response = client.put(
                self.concat_url(f"osint-sources/{source_id}/icon"),
                data={"file": (BytesIO(_INVALID_IMAGE_BYTES), "icon.png")},
                content_type="multipart/form-data",
            )
            assert response.status_code == 401
            assert response.json["error"] == "not authorized"
        finally:
            client.delete(f"/api/config/osint-sources/{source_id}", headers=auth_header)


class TestWordListConfigApi(BaseTest):
    base_uri = "/api/config"

    def test_import_word_lists_json(self, client, auth_header, cleanup_word_lists):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        file_path = os.path.join(dir_path, "word_list_test_data.json")
        with open(file_path, "rb") as f:
            file_storage = FileStorage(stream=f, filename="word_list_test_data.json", content_type="application/json")
            data = {"file": file_storage}
            response = self.assert_post_data_ok(client, "import-word-lists", data, auth_header)
            assert response.json["count"] == 1
            assert response.json["message"] == "Successfully imported word lists"

    def test_import_word_lists_csv(self, client, auth_header, cleanup_word_lists):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        file_name = "word_list_test_data.csv"
        file_path = os.path.join(dir_path, file_name)
        with open(file_path, "rb") as f:
            file_storage = FileStorage(stream=f, filename=file_name, content_type="text/csv")
            data = {"file": file_storage}
            response = self.assert_post_data_ok(client, "import-word-lists", data, auth_header)
            assert response.json["count"] == 1
            assert response.json["message"] == "Successfully imported word lists"

    def test_export_word_lists(self, client, auth_header, cleanup_word_lists):
        response = self.assert_get_ok(client, "export-word-lists", auth_header)
        exported_word_lists = response.json
        assert "data" in exported_word_lists
        test_word_list = next((word_list for word_list in exported_word_lists["data"] if word_list["name"] == "Test wordlist"), None)
        assert test_word_list
        assert test_word_list["description"] == "Test wordlist."
        assert len(test_word_list["entries"]) == 17

    def test_create_word_lists(self, client, auth_header, cleanup_word_lists):
        response = self.assert_post_ok(client, uri="word-lists", json_data=cleanup_word_lists, auth_header=auth_header)
        assert response.json["message"] == "Word list created successfully"
        assert response.json["id"] == cleanup_word_lists["id"]

    def test_modify_word_list(self, client, auth_header, cleanup_word_lists):
        word_list_data = {
            "description": "Wordy McWordListyFace",
        }
        word_list_id = cleanup_word_lists["id"]
        response = self.assert_put_ok(client, uri=f"word-lists/{word_list_id}", json_data=word_list_data, auth_header=auth_header)
        assert response.json["id"] == f"{word_list_id}"

    def test_get_word_lists(self, client, auth_header, cleanup_word_lists):
        response = self.assert_get_ok(client, "word-lists", auth_header)
        count = response.get_json()["total_count"]
        word_lists = response.get_json()["items"]

        assert count > 0
        assert len(word_lists) > 0

        response = self.assert_get_ok(client, f"word-lists/{cleanup_word_lists['id']}", auth_header)
        assert response.json["id"] == cleanup_word_lists["id"]
        assert response.json["name"] == cleanup_word_lists["name"]
        assert response.json["description"] == "Wordy McWordListyFace"
        assert response.json["usage"] == cleanup_word_lists["usage"]
        assert response.json["link"] == cleanup_word_lists["link"]
        assert response.json["entries"] == cleanup_word_lists["entries"]

    def test_delete_word_list(self, client, auth_header, cleanup_word_lists):
        word_list_id = cleanup_word_lists["id"]
        response = self.assert_delete_ok(client, uri=f"word-lists/{word_list_id}", auth_header=auth_header)
        assert response.json["message"] == f"WordList {word_list_id} deleted"


class TestUserConfigApi(BaseTest):
    base_uri = "/api/config"

    def test_create_user(self, client, auth_header, cleanup_user):
        response = self.assert_post_ok(client, uri="users", json_data=cleanup_user, auth_header=auth_header)
        assert response.json["message"] == f"User {cleanup_user['username']} created"

    def test_modify_user(self, client, auth_header, cleanup_user):
        user_id = cleanup_user["id"]
        user_data = {
            "username": cleanup_user["username"],
            "name": "Testy McTestFace",
        }
        response = self.assert_put_ok(client, uri=f"users/{user_id}", json_data=user_data, auth_header=auth_header)
        assert response.json["message"] == f"User {user_id} updated"

    def test_get_user(self, client, auth_header, cleanup_user):
        user_id = cleanup_user["id"]
        response = self.assert_get_ok(client, f"users?search={cleanup_user['username']}", auth_header)
        assert response.json["total_count"] == 1
        assert response.json["items"][0]["username"] == cleanup_user["username"]
        assert response.json["items"][0]["name"] == "Testy McTestFace"
        assert response.json["items"][0]["id"] == user_id
        assert len(response.json["items"][0]["permissions"]) == 14
        assert "password" not in response.json["items"][0]

    def test_delete_user(self, client, auth_header, cleanup_user):
        user_id = cleanup_user["id"]
        response = self.assert_delete_ok(client, uri=f"users/{user_id}", auth_header=auth_header)
        assert response.json["message"] == f"User {user_id} deleted"


class TestRoleConfigApi(BaseTest):
    base_uri = "/api/config"

    def test_create_role(self, client, auth_header, cleanup_role):
        response = self.assert_post_ok(client, uri="roles", json_data=cleanup_role, auth_header=auth_header)
        assert response.json["message"] == "Role created"
        assert response.json["id"] == cleanup_role["id"]

    def test_modify_role(self, client, auth_header, cleanup_role):
        role_data = {
            "description": "Roly McRoleFace",
            "tlp_level": "clear",
        }
        role_id = cleanup_role["id"]
        response = self.assert_put_ok(client, uri=f"roles/{role_id}", json_data=role_data, auth_header=auth_header)
        assert response.json["id"] == f"{role_id}"

    def test_get_roles(self, client, auth_header, cleanup_role):
        role_id = cleanup_role["id"]
        response = self.assert_get_ok(client, uri=f"roles?search={cleanup_role['name']}", auth_header=auth_header)
        assert response.json["total_count"] == 1
        assert response.json["items"][0]["name"] == cleanup_role["name"]
        assert response.json["items"][0]["description"] == "Roly McRoleFace"
        assert response.json["items"][0]["tlp_level"] == "clear"
        assert response.json["items"][0]["id"] == role_id

    def test_delete_role(self, client, auth_header, cleanup_role):
        role_id = cleanup_role["id"]
        response = self.assert_delete_ok(client, uri=f"roles/{role_id}", auth_header=auth_header)
        assert response.json["message"] == f"Role {role_id} deleted"


class TestOrganizationConfigApi(BaseTest):
    base_uri = "/api/config"

    def test_create_organization(self, client, auth_header, cleanup_organization):
        response = self.assert_post_ok(client, uri="organizations", json_data=cleanup_organization, auth_header=auth_header)
        assert response.json["message"] == "Organization created"
        assert response.json["id"] == cleanup_organization["id"]

    def test_modify_organization(self, client, auth_header, cleanup_organization):
        organization_data = {
            "name": cleanup_organization["name"],
            "description": "Orgy McOrgFace",
        }
        organization_id = cleanup_organization["id"]
        response = self.assert_put_ok(client, uri=f"organizations/{organization_id}", json_data=organization_data, auth_header=auth_header)
        assert response.json["id"] == f"{organization_id}"

    def test_get_organizations(self, client, auth_header, cleanup_organization):
        organization_id = cleanup_organization["id"]
        response = self.assert_get_ok(client, uri=f"organizations?search={cleanup_organization['name']}", auth_header=auth_header)
        assert response.json["total_count"] == 1
        assert response.json["items"][0]["name"] == cleanup_organization["name"]
        assert response.json["items"][0]["description"] == "Orgy McOrgFace"
        assert response.json["items"][0]["id"] == organization_id

    def test_delete_organization(self, client, auth_header, cleanup_organization):
        organization_id = cleanup_organization["id"]
        response = self.assert_delete_ok(client, uri=f"organizations/{organization_id}", auth_header=auth_header)
        assert response.json["message"] == f"Organization {organization_id} deleted"


class TestBotConfigApi(BaseTest):
    base_uri = "/api/config"

    def test_create_bot(self, client, auth_header, cleanup_bot):
        response = self.assert_post_ok(client, uri="bots", json_data=cleanup_bot, auth_header=auth_header)
        assert response.json["message"] == f"Bot {cleanup_bot['name']} created"
        assert response.json["id"] == cleanup_bot["id"]

    def test_modify_bot(self, client, auth_header, cleanup_bot, app):
        from core.model.bot import Bot

        with app.app_context():
            if Bot.get(cleanup_bot["id"]):
                Bot.delete(cleanup_bot["id"])

        self.assert_post_ok(client, uri="bots", json_data=cleanup_bot, auth_header=auth_header)

        bot_data = {
            "name": cleanup_bot["name"],
            "type": cleanup_bot["type"],
            "description": "Boty McBotFace",
            "parameters": {"REFRESH_INTERVAL": "0 */8 * * *"},
        }
        bot_id = cleanup_bot["id"]
        response = self.assert_put_ok(client, uri=f"bots/{bot_id}", json_data=bot_data, auth_header=auth_header)
        assert response.json["id"] == f"{bot_id}"

    def test_modify_bot_can_disable_and_clear_schedule(self, client, auth_header, cleanup_bot, app):
        from core.model.bot import Bot

        bot_id = cleanup_bot["id"]
        with app.app_context():
            if Bot.get(bot_id):
                Bot.delete(bot_id)

        self.assert_post_ok(client, uri="bots", json_data=cleanup_bot, auth_header=auth_header)

        self.assert_put_ok(
            client,
            uri=f"bots/{bot_id}",
            json_data={
                "name": cleanup_bot["name"],
                "type": cleanup_bot["type"],
                "enabled": True,
                "parameters": {
                    "RUN_AFTER_COLLECTOR": "true",
                    "REFRESH_INTERVAL": "0 */8 * * *",
                },
            },
            auth_header=auth_header,
        )

        response = self.assert_put_ok(
            client,
            uri=f"bots/{bot_id}",
            json_data={
                "name": cleanup_bot["name"],
                "type": cleanup_bot["type"],
                "enabled": False,
                "parameters": {
                    "RUN_AFTER_COLLECTOR": "true",
                    "REFRESH_INTERVAL": "",
                },
            },
            auth_header=auth_header,
        )

        assert response.json["id"] == f"{bot_id}"

        with app.app_context():
            updated_bot = Bot.get(bot_id)
            assert updated_bot is not None
            assert updated_bot.enabled is False
            assert updated_bot.get_schedule() == ""
            assert bot_id not in Bot.get_post_collection()

    def test_get_bots(self, client, auth_header, cleanup_bot, app):
        from core.model.bot import Bot

        bot_id = cleanup_bot["id"]
        with app.app_context():
            if Bot.get(bot_id):
                Bot.delete(bot_id)

        self.assert_post_ok(client, uri="bots", json_data=cleanup_bot, auth_header=auth_header)
        self.assert_put_ok(
            client,
            uri=f"bots/{bot_id}",
            json_data={
                "name": cleanup_bot["name"],
                "type": cleanup_bot["type"],
                "description": "Boty McBotFace",
                "parameters": {"REFRESH_INTERVAL": "0 */8 * * *"},
            },
            auth_header=auth_header,
        )

        response = self.assert_get_ok(client, uri=f"bots?search={cleanup_bot['name']}", auth_header=auth_header)
        assert response.json["total_count"] == 1
        assert response.json["items"][0]["name"] == cleanup_bot["name"]
        assert response.json["items"][0]["description"] == "Boty McBotFace"
        assert response.json["items"][0]["id"] == bot_id

    def test_delete_bot(self, client, auth_header, cleanup_bot, app):
        from core.model.bot import Bot

        bot_id = cleanup_bot["id"]
        with app.app_context():
            if Bot.get(bot_id):
                Bot.delete(bot_id)

        self.assert_post_ok(client, uri="bots", json_data=cleanup_bot, auth_header=auth_header)

        response = self.assert_delete_ok(client, uri=f"bots/{bot_id}", auth_header=auth_header)
        assert response.json["message"] == f"Bot {cleanup_bot['name']} deleted"


class TestReportTypeConfigApi(BaseTest):
    base_uri = "/api/config"

    def test_create_report_item_type(self, client, auth_header, cleanup_report_item_type):
        response = self.assert_post_ok(client, uri="report-item-types", json_data=cleanup_report_item_type, auth_header=auth_header)
        assert response.json["message"] == f"ReportItemType {cleanup_report_item_type['title']} added"
        assert response.json["id"] == cleanup_report_item_type["id"]

    def test_modify_report_item_type(self, client, auth_header, cleanup_report_item_type):
        report_item_type_data = {
            "description": "Reporty McReportFace",
        }
        report_item_type_id = cleanup_report_item_type["id"]
        response = self.assert_put_ok(
            client, uri=f"report-item-types/{report_item_type_id}", json_data=report_item_type_data, auth_header=auth_header
        )
        assert response.json["id"] == f"{report_item_type_id}"

    def test_get_report_item_types(self, client, auth_header, cleanup_report_item_type):
        report_item_type_id = cleanup_report_item_type["id"]
        response = self.assert_get_ok(client, uri=f"report-item-types?search={cleanup_report_item_type['title']}", auth_header=auth_header)
        assert response.json["total_count"] == 1
        assert response.json["items"][0]["title"] == cleanup_report_item_type["title"]
        assert response.json["items"][0]["description"] == "Reporty McReportFace"
        assert response.json["items"][0]["id"] == report_item_type_id

    def test_delete_report_item_type(self, client, auth_header, cleanup_report_item_type):
        report_item_type_id = cleanup_report_item_type["id"]
        response = self.assert_delete_ok(client, uri=f"report-item-types/{report_item_type_id}", auth_header=auth_header)
        assert response.json["message"] == f"ReportItemType {report_item_type_id} deleted"


class TestProductTypes(BaseTest):
    base_uri = "/api/config"

    def test_create_product_type(self, client, auth_header, cleanup_product_types):
        response = self.assert_post_ok(client, uri="product-types", json_data=cleanup_product_types, auth_header=auth_header)
        assert response.json["message"] == "Product type created"
        assert response.json["id"] == cleanup_product_types["id"]

    def test_create_product_type_rejects_invalid_template_path(self, client, auth_header):
        response = client.post(
            self.concat_url("product-types"),
            json={
                "title": f"invalid-template-{uuid.uuid4().hex[:8]}",
                "type": "pdf_presenter",
                "description": "Product type desc",
                "parameters": {"TEMPLATE_PATH": "/etc/passwd"},
            },
            headers=auth_header,
        )

        assert response.status_code == 400
        assert response.json["error"] == "Invalid presenter template path"

    def test_modify_product_type(self, client, auth_header, cleanup_product_types):
        product_type_data = {"title": "Producty McProductFace"}
        product_type_id = cleanup_product_types["id"]
        response = self.assert_put_ok(client, uri=f"product-types/{product_type_id}", json_data=product_type_data, auth_header=auth_header)
        assert response.json["message"] == f"Updated product type {product_type_data['title']}"

    def test_modify_product_type_rejects_invalid_template_path(self, client, auth_header):
        payload = {
            "title": f"update-template-{uuid.uuid4().hex[:8]}",
            "type": "pdf_presenter",
            "description": "Product type desc",
            "parameters": {"TEMPLATE_PATH": "pdf_template.html"},
        }
        create_response = client.post(self.concat_url("product-types"), json=payload, headers=auth_header)
        assert create_response.status_code == 201

        product_type_id = create_response.json["id"]
        try:
            response = client.put(
                self.concat_url(f"product-types/{product_type_id}"),
                json={
                    "type": "pdf_presenter",
                    "description": "Product type desc",
                    "parameters": {"TEMPLATE_PATH": "/etc/passwd"},
                },
                headers=auth_header,
            )

            assert response.status_code == 400
            assert response.json["error"] == "Invalid presenter template path"
        finally:
            client.delete(self.concat_url(f"product-types/{product_type_id}"), headers=auth_header)

    def test_get_product_types(self, client, auth_header, cleanup_product_types):
        product_type_type = cleanup_product_types["type"]
        response = self.assert_get_ok(client, uri=f"product-types?search={product_type_type}", auth_header=auth_header)
        assert response.json["items"][0]["type"] == product_type_type
        assert response.json["total_count"] == 2
        assert response.json["templates"]

    def test_delete_product_type(self, client, auth_header, cleanup_product_types):
        product_type_id = cleanup_product_types["id"]
        response = self.assert_delete_ok(client, uri=f"product-types/{product_type_id}", auth_header=auth_header)
        assert response.json["message"] == f"Product type {product_type_id} deleted"


class TestPermissions(BaseTest):
    base_uri = "/api/config"

    def test_get_permission(self, client, auth_header):
        from core.managers.pre_seed_data import permissions

        response = self.assert_get_ok(client, uri="permissions", auth_header=auth_header)
        assert response.json["total_count"] == len(permissions)


class TestAcls(BaseTest):
    base_uri = "/api/config"

    def test_create_acl(self, client, auth_header, cleanup_acls):
        response = self.assert_post_ok(client, uri="acls", json_data=cleanup_acls, auth_header=auth_header)
        assert response.json["message"] == "ACL created"
        assert response.json["id"] == cleanup_acls["id"]

    def test_modify_acl(self, client, auth_header, cleanup_acls):
        acl_id = cleanup_acls["id"]
        acl_data = {"description": "new description"}
        response = self.assert_put_ok(client, uri=f"acls/{acl_id}", json_data=acl_data, auth_header=auth_header)
        assert response.json["id"] == acl_id

    def test_get_acl(self, client, auth_header, cleanup_acls):
        response = self.assert_get_ok(client, uri=f"acls?search={cleanup_acls['name']}", auth_header=auth_header)
        assert response.json["items"][0]["name"] == cleanup_acls["name"]
        assert response.json["items"][0]["description"] == "new description"
        assert response.json["items"][0]["item_type"] == cleanup_acls["item_type"]
        assert response.json["items"][0]["item_id"] == cleanup_acls["item_id"]
        assert response.json["items"][0]["roles"] == cleanup_acls["roles"]

    def test_delete_acl(self, client, auth_header, cleanup_acls):
        acl_id = cleanup_acls["id"]
        response = self.assert_delete_ok(client, uri=f"acls/{acl_id}", auth_header=auth_header)
        assert response.json["message"] == f"RoleBasedAccess {acl_id} deleted"


class TestPublisherPreset(BaseTest):
    base_uri = "/api/config"

    def test_create_publisher_preset(self, client, auth_header, cleanup_publisher_preset):
        response = self.assert_post_ok(client, uri="publishers-presets", json_data=cleanup_publisher_preset, auth_header=auth_header)
        assert response.json["message"] == "Publisher preset created successfully"
        assert response.json["id"] == cleanup_publisher_preset["id"]

    def test_modify_publisher_preset(self, client, auth_header, cleanup_publisher_preset):
        publisher_data = {"description": "new description"}
        publisher_preset_id = cleanup_publisher_preset["id"]
        response = self.assert_put_ok(
            client, uri=f"publishers-presets/{publisher_preset_id}", json_data=publisher_data, auth_header=auth_header
        )
        assert response.json["id"] == publisher_preset_id

    def test_get_publisher_preset(self, client, auth_header, cleanup_publisher_preset):
        response = self.assert_get_ok(client, uri=f"publishers-presets?search={cleanup_publisher_preset['name']}", auth_header=auth_header)
        assert response.json["items"][0]["name"] == cleanup_publisher_preset["name"]
        assert response.json["items"][0]["id"] == cleanup_publisher_preset["id"]
        assert response.json["items"][0]["description"] == "new description"
        assert response.json["items"][0]["type"] == cleanup_publisher_preset["type"]
        assert response.json["items"][0]["parameters"]["FTP_URL"] == cleanup_publisher_preset["parameters"]["FTP_URL"]

    def test_delete_publisher_preset(self, client, auth_header, cleanup_publisher_preset):
        publisher_preset_id = cleanup_publisher_preset["id"]
        response = self.assert_delete_ok(client, uri=f"publishers-presets/{publisher_preset_id}", auth_header=auth_header)
        assert response.json["message"] == "PublisherPreset 42 deleted"


class TestAttributes(BaseTest):
    base_uri = "/api/config"

    def test_get_attributes_is_forbidden_for_non_admin_user(self, client, auth_header_user_permissions):
        response = client.get(self.concat_url("attributes"), headers=auth_header_user_permissions)
        assert response.status_code == 403
        assert response.get_json() == {"error": "forbidden"}

    def test_create_attribute(self, client, auth_header, cleanup_attribute):
        response = self.assert_post_ok(client, uri="attributes", json_data=cleanup_attribute, auth_header=auth_header)
        assert response.json["id"] == cleanup_attribute["id"]
        assert response.json["message"] == "Attribute added"

    def test_modify_attribute(self, client, auth_header, cleanup_attribute):
        attribute_data = {"name": "Attributify McAttributeFace"}
        attribute_id = cleanup_attribute["id"]
        response = self.assert_put_ok(client, uri=f"attributes/{attribute_id}", json_data=attribute_data, auth_header=auth_header)
        assert response.json["id"] == attribute_id

    def test_get_attribute(self, client, auth_header, cleanup_attribute):
        attribute_id = cleanup_attribute["id"]
        response = self.assert_get_ok(client, uri=f"attributes/{attribute_id}", auth_header=auth_header)
        assert response.json["id"] == attribute_id

    def test_delete_attribute(self, client, auth_header, cleanup_attribute):
        attribute_id = cleanup_attribute["id"]
        response = self.assert_delete_ok(client, uri=f"attributes/{attribute_id}", auth_header=auth_header)
        assert response.json["message"] == "Attribute 42 deleted"


class TestWorkerTypes(BaseTest):
    base_uri = "/api/config"

    def test_get_worker_types(self, client, cleanup_worker_types, auth_header):
        response = self.assert_get_ok(client, uri=f"worker-types?search={cleanup_worker_types['name']}", auth_header=auth_header)
        assert response.json["items"][0]["name"] == cleanup_worker_types["name"]
        assert response.json["items"][0]["description"] == cleanup_worker_types["description"]
        assert response.json["items"][0]["type"] == cleanup_worker_types["type"]
        assert response.json["items"][0]["parameters"] == cleanup_worker_types["parameters"]

    def test_patch_worker_types(self, client, cleanup_worker_types, auth_header):
        update_data = {"name": "Worky McWorkerFace"}

        response = self.assert_patch_ok(
            client, uri=f"worker-types/{cleanup_worker_types['id']}", json_data=update_data, auth_header=auth_header
        )
        assert response.json["name"] == update_data["name"]
        assert response.json["description"] == cleanup_worker_types["description"]
        assert response.json["type"] == cleanup_worker_types["type"]
        assert response.json["parameters"] == cleanup_worker_types["parameters"]
