import pytest


@pytest.fixture(scope="session")
def fake_source(app, request):
    with app.app_context():
        from core.model.osint_source import OSINTSource

        ossi = {
            "id": "fake-source-id",
            "description": "",
            "name": "Some Bind",
            "parameter_values": [
                {
                    "value": "https://www.some.bind.it/SiteGlobals/Functions/RSSFeed/RSSNewsfeed/RSSNewsfeed.xml",
                    "parameter": "FEED_URL",
                },
            ],
            "collector": {"type": "RSS_COLLECTOR"},
        }

        OSINTSource.add(ossi)

        def teardown():
            with app.app_context():
                OSINTSource.delete(ossi["id"])

        request.addfinalizer(teardown)

        yield ossi["id"]


@pytest.fixture
def news_items_data(app, fake_source):
    with app.app_context():
        from core.model.news_item import NewsItemData

        news_items_data_list = [
            {
                "id": "1be00eef-6ade-4818-acfc-25029531a9a5",
                "content": "TEST CONTENT YYYY",
                "source": "https: //www.some.link/RSSNewsfeed.xml",
                "title": "Mobile World Congress 2023",
                "author": "",
                "collected": "2022-02-21T15:00:14.086285",
                "hash": "82e6e99403686a1072d0fb2013901b843a6725ba8ac4266270f62b7614ec1adf",
                "attributes": [],
                "review": "",
                "link": "https://www.some.other.link/2023.html",
                "osint_source_id": fake_source,
                "published": "2022-02-21T15:01:14.086285",
            },
            {
                "id": "0a129597-592d-45cb-9a80-3218108b29a0",
                "content": "TEST CONTENT XXXX",
                "source": "https: //www.content.xxxx.link/RSSNewsfeed.xml",
                "title": "Bundesinnenministerin Nancy Faeser wird Claudia Plattner zur neuen BSI-Präsidentin berufen",
                "author": "",
                "collected": "2023-01-20T15:00:14.086285",
                "hash": "e270c3a7d87051dea6c3dc14234451f884b427c32791862dacdd7a3e3d318da6",
                "attributes": [],
                "review": "Claudia Plattner wird ab 1. Juli 2023 das Bundesamt für Sicherheitin der Informationstechnik (BSI) leiten.",
                "link": "https: //www.some.other.link/BSI-Praesidentin_230207.html",
                "osint_source_id": fake_source,
                "published": "2023-01-20T19:15:00+01:00",
            },
        ]

        yield NewsItemData.load_multiple(news_items_data_list)


@pytest.fixture
def news_item_aggregates(app, request, news_items_data):
    with app.app_context():
        from core.model.news_item import NewsItemAggregate
        from core.model.user import User

        nia = NewsItemAggregate()
        nia1 = nia.create_new_for_group(news_items_data[0], "default")
        nia2 = nia.create_new_for_group(news_items_data[1], "default")

        def teardown():
            nia = NewsItemAggregate()
            user = User.find_by_name("admin")
            news_item_aggregates, _ = nia.get_by_filter({"group": "default"}, user)
            for aggregate in news_item_aggregates:
                aggregate.delete(user)

        request.addfinalizer(teardown)

        yield [nia1, nia2]


class TestAssessApi(object):
    base_uri = "/api/v1/assess"

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

    def test_get_ManualOSINTSources_auth(self, client, auth_header):
        """
        This test queries the ManualOSINTSources authenticated.
        It expects a valid data and a valid status-code
        """
        self.assert_get_ok(client, "manual-osint-sources", auth_header)

    def test_get_ManualOSINTSources_unauth(self, client):
        """
        This test queries the ManualOSINTSources UNauthenticated.
        It expects "not authorized"
        """
        self.assert_get_failed(client, "manual-osint-sources")

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
    #     response = client.post("/api/v1/assess/news-items", json=news_item, headers=auth_header)
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
        response = client.post("/api/v1/assess/news-items", json=news_item)
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
        response = client.get("/api/v1/assess/news-item-aggregates", headers=auth_header)
        assert response
        assert response.data
        assert response.get_json()["total_count"] == 2
        assert response.content_type == "application/json"
        assert response.status_code == 200

        response = client.get("/api/v1/assess/news-item-aggregates?search=notexistent", headers=auth_header)
        assert response.get_json()["total_count"] == 0

        response = client.get("/api/v1/assess/news-item-aggregates?notexistent=notexist", headers=auth_header)
        assert response.get_json()["total_count"] > 0

        response = client.get("/api/v1/assess/news-item-aggregates?read", headers=auth_header)
        assert len(response.get_json()["items"]) == 0

        response = client.get("/api/v1/assess/news-item-aggregates?relevant", headers=auth_header)
        assert len(response.get_json()["items"]) == 0

        response = client.get("/api/v1/assess/news-item-aggregates?in_report", headers=auth_header)
        assert len(response.get_json()["items"]) == 0

        response = client.get("/api/v1/assess/news-item-aggregates?range=DAY", headers=auth_header)
        assert response.get_json()["total_count"] == 0

        response = client.get("/api/v1/assess/news-item-aggregates?sort=DATE_DESC", headers=auth_header)
        assert response.get_json()["total_count"] > 0

        response = client.get("/api/v1/assess/news-item-aggregates?offset=1", headers=auth_header)
        assert len(response.get_json()["items"]) == 1

        response = client.get("/api/v1/assess/news-item-aggregates?limit=1", headers=auth_header)
        assert len(response.get_json()["items"]) == 1

    def test_get_NewsItem_unauth(self, client):
        """
        This test queries the NewsItems UNauthenticated.
        It expects "not authorized"
        """
        response = client.get("/api/v1/assess/news-items")
        assert response
        assert response.content_type == "application/json"
        assert response.get_json()["error"] == "not authorized"
        assert response.status_code == 401

    def test_get_NewsItem_auth(self, client, news_item_aggregates, auth_header):
        """
        This test queries the NewsItems Authenticated.
        It expects valid NewsItems
        """
        response = client.get("/api/v1/assess/news-items", headers=auth_header)
        assert response
        assert response.data
        assert response.content_type == "application/json"
        assert response.status_code == 200
        print(response.get_json())
        assert len(response.get_json()["items"]) == 2

    def test_get_NewsItemAggregatesTags_unauth(self, client):
        """
        This test queries the NewsItemsAggregatesTags UNauthenticated.
        It expects "not authorized"
        """
        response = client.get("/api/v1/assess/tags")
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
        response = nia2.update_tags(nia2.id, {"foo": {"type": "misc"}, "bar": {"type": "misc"}})
        assert response[1] == 200

        response = client.get("/api/v1/assess/tags", headers=auth_header)
        assert response
        assert response.data
        print(response.get_json())
        assert len(response.get_json()) == 0
        assert response.content_type == "application/json"
        assert response.status_code == 200
        response = client.get("/api/v1/assess/tags?min_size=1", headers=auth_header)
        assert len(response.get_json()) == 3
        response = client.get("/api/v1/assess/tags?search=fo&min_size=1", headers=auth_header)
        assert len(response.get_json()) == 1
        response = client.get("/api/v1/assess/tags?limit=1&min_size=1", headers=auth_header)
        assert len(response.get_json()) == 1
        response = client.get("/api/v1/assess/tags?offset=1&min_size=1", headers=auth_header)
        assert len(response.get_json()) == 2
