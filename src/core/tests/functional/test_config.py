import os
import json
from tests.functional.helpers import BaseTest
from werkzeug.datastructures import FileStorage


class TestSourcesConfigApi(BaseTest):
    base_uri = "/api/v1/config"

    def test_import_osint_sources(self, client, auth_header, cleanup_sources):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        file_path = os.path.join(dir_path, "osint_sources_test_data_v1.json")
        with open(file_path, "rb") as f:
            file_storage = FileStorage(stream=f, filename="osint_sources_test_data_v1.json", content_type="application/json")
            data = {"file": file_storage}
            response = self.assert_post_data_ok(client, "import-osint-sources", data, auth_header)
            assert response.json["count"] == 6
            assert response.json["message"] == "Successfully imported sources"

    def test_export_osint_sources(self, client, auth_header, cleanup_sources):
        response = self.assert_get_ok(client, "export-osint-sources", auth_header)
        dir_path = os.path.dirname(os.path.realpath(__file__))
        file_path = os.path.join(dir_path, "osint_sources_test_data_v2.json")
        with open(file_path, "rb") as f:
            test_data = json.load(f)
            test_result = response.json
            for source in test_data["data"]:
                assert source in test_result["data"]

    def test_create_source(self, client, auth_header, cleanup_sources):
        response = self.assert_post_ok(client, uri="osint-sources", json_data=cleanup_sources, auth_header=auth_header)
        assert response.json["message"] == "OSINT source created successfully"
        assert response.json["id"] == cleanup_sources["id"]

    def test_modify_source(self, client, auth_header, cleanup_sources):
        source_data = {
            "description": "Sourcy McSourceFace",
        }
        source_id = cleanup_sources["id"]
        response = self.assert_put_ok(client, uri=f"osint-sources/{source_id}", json_data=source_data, auth_header=auth_header)
        assert response.json["id"] == f"{source_id}"

    def test_get_sources(self, client, auth_header, cleanup_sources):
        source_id = cleanup_sources["id"]
        response = self.assert_get_ok(client, uri=f"osint-sources?search={cleanup_sources['name']}", auth_header=auth_header)
        assert response.json["total_count"] == 1
        assert response.json["items"][0]["name"] == cleanup_sources["name"]
        assert response.json["items"][0]["description"] == "Sourcy McSourceFace"
        assert response.json["items"][0]["id"] == source_id

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


class TestWordListConfigApi(BaseTest):
    base_uri = "/api/v1/config"

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
        dir_path = os.path.dirname(os.path.realpath(__file__))
        file_path = os.path.join(dir_path, "word_list_test_data.json")
        with open(file_path, "rb") as f:
            exported_word_lists = response.json
            assert "data" in exported_word_lists
            print(exported_word_lists["data"])
            test_word_list = next((word_list for word_list in exported_word_lists["data"] if word_list["name"] == "Test wordlist"), None)
            assert test_word_list
            assert test_word_list["description"] == "Test wordlist."
            assert len(test_word_list["entries"]) == 17

    def test_get_word_lists(self, client, auth_header, cleanup_word_lists):
        response = self.assert_get_ok(client, "word-lists", auth_header)
        totoal_count = response.get_json()["total_count"]
        word_lists = response.get_json()["items"]

        assert totoal_count > 0
        assert len(word_lists) > 0


class TestUserConfigApi(BaseTest):
    base_uri = "/api/v1/config"

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
        assert response.json[0]["message"] == f"User {user_id} updated"

    def test_get_user(self, client, auth_header, cleanup_user):
        user_id = cleanup_user["id"]
        response = self.assert_get_ok(client, f"users?search={cleanup_user['username']}", auth_header)
        assert response.json["total_count"] == 1
        assert response.json["items"][0]["username"] == cleanup_user["username"]
        assert response.json["items"][0]["name"] == "Testy McTestFace"
        assert response.json["items"][0]["id"] == user_id
        assert "password" not in response.json["items"][0]

    def test_delete_user(self, client, auth_header, cleanup_user):
        user_id = cleanup_user["id"]
        response = self.assert_delete_ok(client, uri=f"users/{user_id}", auth_header=auth_header)
        assert response.json[0]["message"] == f"User {user_id} deleted"

    def test_create_role(self, client, auth_header, cleanup_role):
        response = self.assert_post_ok(client, uri="roles", json_data=cleanup_role, auth_header=auth_header)
        assert response.json["message"] == "Role created"
        assert response.json["id"] == cleanup_role["id"]

    def test_modify_role(self, client, auth_header, cleanup_role):
        role_data = {
            "description": "Roly McRoleFace",
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
        assert response.json["items"][0]["id"] == role_id

    def test_delete_role(self, client, auth_header, cleanup_role):
        role_id = cleanup_role["id"]
        response = self.assert_delete_ok(client, uri=f"roles/{role_id}", auth_header=auth_header)
        assert response.json["message"] == f"Role {role_id} deleted"

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
    base_uri = "/api/v1/config"

    def test_create_bot(self, client, auth_header, cleanup_bot):
        response = self.assert_post_ok(client, uri="bots", json_data=cleanup_bot, auth_header=auth_header)
        assert response.json["message"] == f"Bot {cleanup_bot['name']} added"
        assert response.json["id"] == cleanup_bot["id"]

    def test_modify_bot(self, client, auth_header, cleanup_bot):
        bot_data = {
            "name": cleanup_bot["name"],
            "type": cleanup_bot["type"],
            "description": "Boty McBotFace",
        }
        bot_id = cleanup_bot["id"]
        response = self.assert_put_ok(client, uri=f"bots/{bot_id}", json_data=bot_data, auth_header=auth_header)
        assert response.json["id"] == f"{bot_id}"

    def test_get_bots(self, client, auth_header, cleanup_bot):
        bot_id = cleanup_bot["id"]
        response = self.assert_get_ok(client, uri=f"bots?search={cleanup_bot['name']}", auth_header=auth_header)
        assert response.json["total_count"] == 1
        assert response.json["items"][0]["name"] == cleanup_bot["name"]
        assert response.json["items"][0]["description"] == "Boty McBotFace"
        assert response.json["items"][0]["id"] == bot_id

    def test_delete_bot(self, client, auth_header, cleanup_bot):
        bot_id = cleanup_bot["id"]
        response = self.assert_delete_ok(client, uri=f"bots/{bot_id}", auth_header=auth_header)
        assert response.json["message"] == f"Bot {bot_id} deleted"


class TestReportTypeConfigApi(BaseTest):
    base_uri = "/api/v1/config"

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
