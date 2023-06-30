class TestConfigApi(object):
    base_uri = "/api/v1/config"

    def assert_get_ok(self, client, uri, auth_header):
        response = client.get(f"{self.base_uri}/{uri}", headers=auth_header)
        assert response
        assert response.content_type == "application/json"
        assert response.data
        assert response.status_code == 200
        return response

    def assert_get_failed(self, client, uri):
        response = client.get(f"{self.base_uri}/{uri}")
        assert response
        assert response.content_type == "application/json"
        assert response.get_json()["error"] == "not authorized"
        assert response.status_code == 401
        return response

    def test_attributes_get(self, client, auth_header):
        response = self.assert_get_ok(client, "attributes", auth_header)

        # assert response.json == attr_data

    def test_attribute_get(self, client, auth_header):
        response = self.assert_get_ok(client, "attributes/1", auth_header)
        # assert response.json == attr_data[0]

    def test_attribute_enums_get(self, client, auth_header):
        response = self.assert_get_ok(client, "attributes/1/enums", auth_header)

        # assert response.json == attr_enum_data

    def test_report_item_types_config_get(self, client, auth_header):
        response = self.assert_get_ok(client, "report-item-types", auth_header)

        # assert response.json == report_item_types_config_data

    def test_product_types_get(self, client, auth_header):
        response = self.assert_get_ok(client, "product-types", auth_header)
        items = response.json["items"]
        assert items == []
        # assert response.json == product_types_data

    def test_permissions_get(self, client, auth_header):
        response = self.assert_get_ok(client, "permissions", auth_header)

        # assert response.json == permissions_data

    def test_external_permissions_get(self, client, auth_header):
        response = self.assert_get_ok(client, "external-permissions", auth_header)

        # assert response.json == external_permissions_data
