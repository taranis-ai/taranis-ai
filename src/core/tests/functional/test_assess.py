from tests.functional.helpers import BaseTest


class TestAssessApi(BaseTest):
    base_uri = "/api/assess"

    def test_get_OSINTSourceGroupsAssess_auth(self, client, auth_header):
        """
        This test queries the OSINTSourceGroupsAssess authenticated.
        It expects a valid data and a valid status-code
        """
        response = self.assert_get_ok(client, "osint-source-groups", auth_header)
        assert response.get_json()["items"][0]["id"] == "default"

    def test_get_OSINTSourceGroupsAssess_unauth(self, client):
        """
        This test queries the OSINTSourceGroupsAssess UNauthenticated.
        It expects "not authorized"
        """
        self.assert_get_failed(client, "osint-source-groups")

    def test_get_OSINTSourceGroupsList_auth(self, client, auth_header):
        """
        This test queries the OSINTSourceGroupsList authenticated.
        It expects a valid data and a valid status-code
        """
        self.assert_get_ok(client, "osint-source-group-list", auth_header)

    def test_get_OSINTSourceGroupsList_unauth(self, client):
        """
        This test queries the OSINTSourceGroupsList UNauthenticated.
        It expects "not authorized"
        """
        self.assert_get_failed(client, "osint-source-group-list")

    def test_get_OSINTSourcesList_auth(self, client, auth_header):
        """
        This test queries the OSINTSourcesList authenticated.
        It expects a valid data and a valid status-code
        """
        self.assert_get_ok(client, "osint-sources-list", auth_header)

    def test_get_OSINTSourcesList_unauth(self, client):
        """
        This test queries the OSINTSourcesList UNauthenticated.
        It expects "not authorized"
        """
        self.assert_get_failed(client, "osint-sources-list")

    # def test_post_AddNewsItem_auth(self, client, news_item_aggregates, auth_header):
    #     """
    #     This test queries the AddNewsItem authenticated.
    #     It expects a valid data and a valid status-code
    #     """
    #     attribs = {"key": "1293", "value": "some value", "binary_mime_type": "dGVzdAo=", "binary_value": "dGVzdAo="}

    #     news_item = {
    #         "id": "1337",
    #         "title": "test title",
    #         "review": "test review",
    #         "source": "test source",
    #         "link": "https://linky.link.lnk",
    #         "hash": "test hash",
    #         "published": "2022-02-21T15:00:15.086285",
    #         "author": "James Bond",
    #         "content": "Diamonds are forever",
    #         "collected": "2022-02-21T15:00:14.086285",
    #         "attributes": [attribs],
    #     }
    #     before = news_item_data.count_all()
    #     response = client.post("/api/assess/news-items", json=news_item, headers=auth_header)
    #     assert response
    #     assert response.content_type == "application/json"
    #     assert response.data
    #     assert response.status_code == 200
    #     assert before < news_item_data.count_all()

    def test_post_AddNewsItem_unauth(self, client, news_items_data):
        """
        This test queries the AddNewsItem UNauthenticated.
        It expects "not authorized"
        """
        attribs = {"key": "1293", "value": "some value", "binary_mime_type": "dGVzdAo=", "binary_value": "dGVzdAo="}

        news_item = {
            "id": "1337",
            "title": "test title",
            "review": "test review",
            "source": "test source",
            "link": "https://linky.link.lnk",
            "hash": "test hash",
            "published": "2022-02-21T15:00:15.086285",
            "author": "James Bond",
            "content": "Diamonds are forever",
            "collected": "2022-02-21T15:00:14.086285",
            "attributes": [attribs],
        }
        before = len(news_items_data)
        response = client.post("/api/assess/news-items", json=news_item)
        assert response
        assert response.content_type == "application/json"
        assert response.get_json()["error"] == "not authorized"
        assert response.status_code == 401
        assert before == len(news_items_data)

    def test_get_NewsItemAggregates_auth(self, client, news_item_aggregates, auth_header):
        """
        This test queries the NewsItemAggregates authenticated.
        It expects a valid data and a valid status-code
        """
        response = client.get("/api/assess/news-item-aggregates", headers=auth_header)
        assert response
        assert response.data
        assert response.get_json()["total_count"] == 2
        assert response.content_type == "application/json"
        assert response.status_code == 200

        response = client.get("/api/assess/news-item-aggregates?search=notexistent", headers=auth_header)
        assert response.get_json()["total_count"] == 0

        response = client.get("/api/assess/news-item-aggregates?notexistent=notexist", headers=auth_header)
        assert response.get_json()["total_count"] > 0

        response = client.get("/api/assess/news-item-aggregates?read", headers=auth_header)
        assert len(response.get_json()["items"]) == 0

        response = client.get("/api/assess/news-item-aggregates?relevant", headers=auth_header)
        assert len(response.get_json()["items"]) == 0

        response = client.get("/api/assess/news-item-aggregates?in_report", headers=auth_header)
        assert len(response.get_json()["items"]) == 0

        response = client.get("/api/assess/news-item-aggregates?range=DAY", headers=auth_header)
        assert response.get_json()["total_count"] == 0

        response = client.get("/api/assess/news-item-aggregates?sort=DATE_DESC", headers=auth_header)
        assert response.get_json()["total_count"] > 0

        response = client.get("/api/assess/news-item-aggregates?offset=1", headers=auth_header)
        assert len(response.get_json()["items"]) == 1

        response = client.get("/api/assess/news-item-aggregates?limit=1", headers=auth_header)
        assert len(response.get_json()["items"]) == 1

    def test_get_NewsItem_unauth(self, client):
        """
        This test queries the NewsItems UNauthenticated.
        It expects "not authorized"
        """
        response = client.get("/api/assess/news-items")
        assert response
        assert response.content_type == "application/json"
        assert response.get_json()["error"] == "not authorized"
        assert response.status_code == 401

    def test_get_NewsItem_auth(self, client, news_item_aggregates, auth_header):
        """
        This test queries the NewsItems Authenticated.
        It expects valid NewsItems
        """
        response = client.get("/api/assess/news-items", headers=auth_header)
        assert response
        assert response.data
        assert response.content_type == "application/json"
        assert response.status_code == 200
        assert len(response.get_json()["items"]) == 2

    def test_get_NewsItemAggregatesTags_unauth(self, client):
        """
        This test queries the NewsItemsAggregatesTags UNauthenticated.
        It expects "not authorized"
        """
        response = client.get("/api/assess/tags")
        assert response
        assert response.content_type == "application/json"
        assert response.get_json()["error"] == "not authorized"
        assert response.status_code == 401

    def test_get_NewsItemAggregatesTags(self, client, news_item_aggregates, auth_header):
        """
        This test queries the NewsItemsAggregatesTags Authentictaed.
        It expects a list of tags
        """
        nia1, nia2 = news_item_aggregates
        response = nia1.update_tags(nia1.id, ["foo", "bar", "baz"])
        assert response[1] == 200
        response = nia2.update_tags(nia2.id, {"foo": {"tag_type": "misc"}, "bar": {"tag_type": "misc"}})
        assert response[1] == 200

        response = client.get("/api/assess/tags", headers=auth_header)
        assert response
        assert response.data
        assert len(response.get_json()) == 0
        assert response.content_type == "application/json"
        assert response.status_code == 200
        response = client.get("/api/assess/tags?min_size=1", headers=auth_header)
        assert len(response.get_json()) == 3
        response = client.get("/api/assess/tags?search=fo&min_size=1", headers=auth_header)
        assert len(response.get_json()) == 1
        response = client.get("/api/assess/tags?limit=1&min_size=1", headers=auth_header)
        assert len(response.get_json()) == 1
        response = client.get("/api/assess/tags?offset=1&min_size=1", headers=auth_header)
        assert len(response.get_json()) == 2
