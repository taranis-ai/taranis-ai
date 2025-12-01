from tests.functional.helpers import BaseTest


class TestPublishApi(BaseTest):
    base_uri = "/api/publish"

    def test_post_Product(self, client, auth_header, cleanup_product):
        """
        This test queries the /api/publish/products endpoint with a POST request.
        It expects a valid data and a valid status-code
        """
        response = self.assert_post_ok(client, "products", auth_header=auth_header, json_data=cleanup_product)
        assert response.get_json()["id"] == cleanup_product["id"]

    def test_get_Products(self, client, auth_header, cleanup_product):
        """
        This test queries the /api/publish/products endpoint.
        It expects a valid data and a valid status-code
        """
        response = self.assert_get_ok(client, "products", auth_header)
        assert response.get_json()["total_count"] == 1
        assert response.get_json()["items"][0]["title"] == cleanup_product["title"]


class TestAutoPublishApi(BaseTest):
    base_publish_uri = "/api/publish"
    base_analyze_uri = "/api/analyze"
    base_worker_uri = "/api/worker"
    base_admin_uri = "/api/config"

    # TODO: preliminary test
    def test_autopublish_on_product_update(
        self, client, auth_header, api_header, cleanup_product, cleanup_report_item, full_story, cleanup_publisher
    ):
        """
        This test updates a product with auto_publish enabled using the test client so different base URIs can be used.
        """

        publish_base = self.base_publish_uri
        analyze_base = self.base_analyze_uri
        admin_base = self.base_admin_uri

        headers = auth_header or {}

        # Create publisher
        resp = client.post(f"{admin_base}/publishers-presets", headers=headers, json=cleanup_publisher)
        assert resp.status_code == 200, resp.get_data(as_text=True)

        # Ensure the product has auto_publish set to True and create it
        cleanup_product["auto_publish"] = True
        cleanup_product["default_publisher"] = cleanup_publisher["id"]
        resp = client.post(f"{publish_base}/products", headers=headers, json=cleanup_product)
        assert resp.status_code == 201, resp.get_data(as_text=True)
        created = resp.get_json()
        product_obj = created.get("product", created)
        assert product_obj.get("auto_publish") is True
        product_id = cleanup_product.get("id")

        # Create report item
        resp = client.post(f"{analyze_base}/report-items", headers=headers, json=cleanup_report_item)
        assert resp.status_code == 200, resp.get_data(as_text=True)
        report_item_json = resp.get_json()
        assert report_item_json.get("report", {}).get("title") == cleanup_report_item["title"]

        # # create story
        # resp = client.post(f"{worker_base}/stories", headers=api_header, json=full_story[0])
        # assert resp.status_code == 200, resp.get_data(as_text=True)
        # story_json = resp.get_json()
        # assert story_json.get("message") == "Story added successfully"

        # # Attach story to report-item
        # resp = client.put(
        #     f"{analyze_base}/report-items/{cleanup_report_item['id']}",
        #     headers=headers,
        #     json={"story_ids": [full_story[0]["id"]]},
        # )
        # assert resp.status_code == 200, resp.get_data(as_text=True)

        # fetch current product to discover associated report id
        resp = client.get(f"{publish_base}/products/{product_id}", headers=headers)
        assert resp.status_code == 200, resp.get_data(as_text=True)
        prod_json = resp.get_json()
        product_obj = prod_json.get("product", prod_json)

        # update the report to trigger autopublish (use analyze base for reports)
        report_id = cleanup_report_item.get("id")
        report_update = {"title": "Updated Report Title for AutoPublish"}
        resp = client.put(f"{analyze_base}/report/{report_id}", headers=headers, json=report_update)
        assert resp.status_code == 200, resp.get_data(as_text=True)
