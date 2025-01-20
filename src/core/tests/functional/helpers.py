class BaseTest:
    base_uri = "/api/"

    def concat_url(self, uri):
        return f"{self.base_uri}/{uri}" if uri[0] != "/" else f"{self.base_uri}{uri}"

    def assert_get_ok(self, client, uri, auth_header):
        response = client.get(self.concat_url(uri), headers=auth_header)
        return self.assert_json_ok(response)

    def assert_post_ok(self, client, uri, json_data, auth_header):
        response = client.post(self.concat_url(uri), json=json_data, headers=auth_header)
        return self.assert_json_ok(response)

    def assert_patch_ok(self, client, uri, json_data, auth_header):
        response = client.patch(self.concat_url(uri), json=json_data, headers=auth_header)
        return self.assert_json_ok(response)

    def assert_post_data_ok(self, client, uri, data, auth_header):
        auth_header["Content-type"] = "multipart/form-data"
        response = client.post(self.concat_url(uri), data=data, headers=auth_header)
        return self.assert_json_ok(response)

    def assert_get_files_ok(self, client, uri, auth_header):
        response = client.get(self.concat_url(uri), headers=auth_header)
        return self.assert_file_ok(response)

    def assert_put_ok(self, client, uri, json_data, auth_header):
        response = client.put(self.concat_url(uri), json=json_data, headers=auth_header)
        return self.assert_json_ok(response)

    def assert_delete_ok(self, client, uri, auth_header):
        response = client.delete(self.concat_url(uri), headers=auth_header)
        return self.assert_json_ok(response)

    def assert_file_ok(self, response):
        return self.assert_ok(response, "text/html; charset=utf-8")

    def assert_json_ok(self, response):
        return self.assert_ok(response, "application/json")

    def assert_ok(self, response, content_type):
        assert response
        assert response.content_type == content_type
        assert response.data
        assert response.status_code < 300
        return response

    def assert_get_failed(self, client, uri):
        response = client.get(f"{self.base_uri}/{uri}")
        assert response
        assert response.content_type == "application/json"
        assert response.get_json()["error"] == "not authorized"
        assert response.status_code == 401
        return response
