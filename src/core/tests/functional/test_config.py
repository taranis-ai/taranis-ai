import os
import json
from tests.functional.helpers import BaseTest
from werkzeug.datastructures import FileStorage


class TestSourcesConfigApi(BaseTest):
    base_uri = "/api/config"

    def test_import_osint_sources(self, client, auth_header, cleanup_sources):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        file_path = os.path.join(dir_path, "osint_sources_test_data_v1.json")
        with open(file_path, "rb") as f:
            file_storage = FileStorage(stream=f, filename="osint_sources_test_data_v1.json", content_type="application/json")
            data = {"file": file_storage}
            response = self.assert_post_data_ok(client, uri="import-osint-sources", data=data, auth_header=auth_header)
            assert response.json["count"] == 6
            assert response.json["message"] == "Successfully imported sources"

    def test_export_osint_sources(self, client, auth_header, cleanup_sources):
        response = self.assert_get_ok(client, uri="export-osint-sources", auth_header=auth_header)
        dir_path = os.path.dirname(os.path.realpath(__file__))
        file_path = os.path.join(dir_path, "osint_sources_test_data_v2.json")
        with open(file_path, "rb") as f:
            test_data = json.load(f)
            test_result = response.json
            for source in test_data["data"]:
                assert source in test_result["sources"]

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
        print(exported_word_lists["data"])
        test_word_list = next((word_list for word_list in exported_word_lists["data"] if word_list["name"] == "Test wordlist"), None)
        assert test_word_list
        assert test_word_list["description"] == "Test wordlist."
        assert len(test_word_list["entries"]) == 17

    def test_create_word_lists(self, client, auth_header, cleanup_word_lists):
        response = self.assert_post_ok(client, uri="word-lists", json_data=cleanup_word_lists, auth_header=auth_header)
        assert response.json["message"] == f"Word list created successfully"
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
        total_count = response.get_json()["total_count"]
        word_lists = response.get_json()["items"]

        assert total_count > 0
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
    base_uri = "/api/config"

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
        assert response.json["message"] == f"Product type created"
        assert response.json["id"] == cleanup_product_types["id"]

    def test_modify_product_type(self, client, auth_header, cleanup_product_types):
        product_type_data = {"title": "Producty McProductFace"}
        product_type_id = cleanup_product_types["id"]
        response = self.assert_put_ok(client, uri=f"product-types/{product_type_id}", json_data=product_type_data, auth_header=auth_header)
        assert response.json == product_type_id

    def test_get_product_types(self, client, auth_header, cleanup_product_types):
        product_type_type = cleanup_product_types["type"]
        response = self.assert_get_ok(client, uri=f"product-types?search={product_type_type}", auth_header=auth_header)
        # TODO: check why only one search is found when there are more in the DB
        # assert response.json["total_count"] == 1
        # assert response.json["items"][0]["title"] == "Test Role"
        # assert response.json["items"][0]["type"] == "pdf_presenter"
        # assert response.json["items"][0]["id"] == 42

    def test_delete_product_type(self, client, auth_header, cleanup_product_types):
        product_type_id = cleanup_product_types["id"]
        response = self.assert_delete_ok(client, uri=f"product-types/{product_type_id}", auth_header=auth_header)
        assert response.json["message"] == f"ProductType {product_type_id} deleted"


class TestPermissions(BaseTest):
    base_uri = "/api/config"

    def test_get_permission(self, client, auth_header, permissions):
        response = self.assert_get_ok(client, uri=f"permissions?search={permissions[0]}", auth_header=auth_header)
        assert response.json["total_count"] == 1
        assert response.json["items"][0]["id"] == permissions[0]


class TestAcls(BaseTest):
    base_uri = "/api/config"

    def test_create_acl(self, client, auth_header, cleanup_acls):
        response = self.assert_post_ok(client, uri="acls", json_data=cleanup_acls, auth_header=auth_header)
        assert response.json["message"] == "ACL created"
        assert response.json["id"] == 42

    def test_modify_acl(self, client, auth_header, cleanup_acls):
        acl_id = cleanup_acls["id"]
        acl_data = {"description": "new description"}
        response = self.assert_put_ok(client, uri=f"acls/{acl_id}", json_data=acl_data, auth_header=auth_header)
        # TODO: add tests after bugfix

    def test_get_acl(self, client, auth_header, cleanup_acls):
        response = self.assert_get_ok(client, uri=f"acls?search={cleanup_acls['name']}", auth_header=auth_header)
        assert response.json["items"][0]["name"] == cleanup_acls["name"]
        assert response.json["items"][0]["description"] == "new description"
        assert response.json["items"][0]["item_type"] == 3  # Number 3 represents an ENUM type
        assert response.json["items"][0]["item_id"] == cleanup_acls["item_id"]
        assert response.json["items"][0]["everyone"] == cleanup_acls["everyone"]
        assert response.json["items"][0]["see"] == cleanup_acls["see"]
        assert response.json["items"][0]["access"] == cleanup_acls["access"]
        assert response.json["items"][0]["modify"] == cleanup_acls["modify"]
        assert response.json["items"][0]["roles"] == cleanup_acls["roles"]
        assert response.json["items"][0]["users"] == cleanup_acls["users"]

    def test_delete_acl(self, client, auth_header, cleanup_acls):
        acl_id = cleanup_acls["id"]
        response = self.assert_delete_ok(client, uri=f"acls/{acl_id}", auth_header=auth_header)
        assert response.json["message"] == f"ACLEntry {acl_id} deleted"


class TestPublisherPreset(BaseTest):
    base_uri = "/api/config"

    def test_create_publisher_preset(self, client, auth_header, cleanup_publisher_preset):
        response = self.assert_post_ok(client, uri="publishers-presets", json_data=cleanup_publisher_preset, auth_header=auth_header)
        assert response.json["message"] == "Publisher preset created successfully"
        assert response.json["id"] == "44"

    def test_modify_publisher_preset(self, client, auth_header, cleanup_publisher_preset):
        publisher_data = {"description": "new description"}
        publisher_preset_id = cleanup_publisher_preset["id"]
        response = self.assert_put_ok(
            client, uri=f"publishers-presets/{publisher_preset_id}", json_data=publisher_data, auth_header=auth_header
        )
        # TODO: add tests after bugfix

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
        assert response.json["message"] == "PublisherPreset 44 deleted"


class TestAttributes(BaseTest):
    base_uri = "/api/config"

    def test_create_attribute(self, client, auth_header, cleanup_attribute):
        response = self.assert_post_ok(client, uri="attributes", json_data=cleanup_attribute, auth_header=auth_header)
        assert response.json["id"] == 42
        assert response.json["message"] == "Attribute added"

    def test_modify_attribute(self, client, auth_header, cleanup_attribute):
        attribute_data = {"name": "Attributify McAttributeFace"}
        attribute_id = cleanup_attribute["id"]
        response = self.assert_put_ok(client, uri=f"attributes/{attribute_id}", json_data=attribute_data, auth_header=auth_header)
        # TODO: add tests after bugfix

    def test_get_attribute(self, client, auth_header, cleanup_attribute):
        attribute_id = cleanup_attribute["id"]
        response = self.assert_get_ok(client, uri=f"attributes/{attribute_id}", auth_header=auth_header)
        # TODO: return value is formatted not correctly - see bug issue
        # TODO: add tests after bugfix

    def test_delete_attribute(self, client, auth_header, cleanup_attribute):
        attribute_id = cleanup_attribute["id"]
        response = self.assert_delete_ok(client, uri=f"attributes/{attribute_id}", auth_header=auth_header)
        assert response.json["message"] == "Attribute 42 deleted"


class TestWorkerTypes(BaseTest):
    base_uri = "/api/config"

    def test_create_worker_types(self, client, auth_header, cleanup_worker_types):
        response = self.assert_post_ok(client, uri="worker-types", json_data=cleanup_worker_types, auth_header=auth_header)
        assert response.json["message"] == f"Worker {cleanup_worker_types['name']} added"

    def test_get_worker_types(self, client, cleanup_worker_types, auth_header):
        response = self.assert_get_ok(client, uri=f"worker-types?search={cleanup_worker_types['name']}", auth_header=auth_header)
        assert response.json["items"][0]["name"] == cleanup_worker_types["name"]
        assert response.json["items"][0]["description"] == cleanup_worker_types["description"]
        assert response.json["items"][0]["type"] == cleanup_worker_types["type"]
        assert response.json["items"][0]["parameters"]["REGULAR_EXPRESSION"] == cleanup_worker_types["parameters"]["REGULAR_EXPRESSION"]
        assert response.json["items"][0]["parameters"]["ITEM_FILTER"] == cleanup_worker_types["parameters"]["ITEM_FILTER"]
        assert response.json["items"][0]["parameters"]["RUN_AFTER_COLLECTOR"] == cleanup_worker_types["parameters"]["RUN_AFTER_COLLECTOR"]
        assert response.json["items"][0]["parameters"]["REFRESH_INTERVAL"] == cleanup_worker_types["parameters"]["REFRESH_INTERVAL"]
