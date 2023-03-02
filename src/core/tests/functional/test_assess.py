from core.model.news_item import NewsItemAggregate


class TestAssessApi(object):
    def test_get_OSINTSourceGroupsAssess_auth(self, client, auth_header):
        """
        This test queries the OSINTSourceGroupsAssess authenticated.
        It expects a valid data and a valid status-code
        """
        response = client.get("/api/v1/assess/osint-source-groups", headers=auth_header)
        assert response
        assert response.content_type == "application/json"
        assert response.data
        assert response.status_code == 200

    def test_get_OSINTSourceGroupsAssess_unauth(self, client):
        """
        This test queries the OSINTSourceGroupsAssess UNauthenticated.
        It expects "not authorized"
        """
        response = client.get("/api/v1/assess/osint-source-groups")
        assert response
        assert response.content_type == "application/json"
        assert response.get_json()["error"] == "not authorized"
        assert response.status_code == 401

    def test_get_OSINTSourceGroupsList_auth(self, client, auth_header):
        """
        This test queries the OSINTSourceGroupsList authenticated.
        It expects a valid data and a valid status-code
        """
        response = client.get("/api/v1/assess/osint-source-group-list", headers=auth_header)
        assert response
        assert response.content_type == "application/json"
        assert response.data
        assert response.status_code == 200

    def test_get_OSINTSourceGroupsList_unauth(self, client):
        """
        This test queries the OSINTSourceGroupsList UNauthenticated.
        It expects "not authorized"
        """
        response = client.get("/api/v1/assess/osint-source-group-list")
        assert response
        assert response.content_type == "application/json"
        assert response.get_json()["error"] == "not authorized"
        assert response.status_code == 401

    def test_get_OSINTSourcesList_auth(self, client, auth_header):
        """
        This test queries the OSINTSourcesList authenticated.
        It expects a valid data and a valid status-code
        """
        response = client.get("/api/v1/assess/osint-sources-list", headers=auth_header)
        assert response
        assert response.content_type == "application/json"
        assert response.data
        assert response.status_code == 200

    def test_get_OSINTSourcesList_unauth(self, client):
        """
        This test queries the OSINTSourcesList UNauthenticated.
        It expects "not authorized"
        """
        response = client.get("/api/v1/assess/osint-sources-list")
        assert response
        assert response.content_type == "application/json"
        assert response.get_json()["error"] == "not authorized"
        assert response.status_code == 401

    def test_get_ManualOSINTSources_auth(self, client, auth_header):
        """
        This test queries the ManualOSINTSources authenticated.
        It expects a valid data and a valid status-code
        """
        response = client.get("/api/v1/assess/manual-osint-sources", headers=auth_header)
        assert response
        assert response.content_type == "application/json"
        assert response.data
        assert response.status_code == 200

    def test_get_ManualOSINTSources_unauth(self, client):
        """
        This test queries the ManualOSINTSources UNauthenticated.
        It expects "not authorized"
        """
        response = client.get("/api/v1/assess/manual-osint-sources")
        assert response
        assert response.content_type == "application/json"
        assert response.get_json()["error"] == "not authorized"
        assert response.status_code == 401

    def test_post_AddNewsItem_auth(self, client, news_item_data, db_session, auth_header):
        """
        This test queries the AddNewsItem authenticated.
        It expects a valid data and a valid status-code
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
        before = news_item_data.count_all()
        response = client.post("/api/v1/assess/news-items", json=news_item, headers=auth_header)
        assert response
        assert response.content_type == "application/json"
        assert response.data
        assert response.status_code == 200
        assert before < news_item_data.count_all()

    def test_post_AddNewsItem_unauth(self, client, news_item_data, db_session):
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
        before = news_item_data.count_all()
        response = client.post("/api/v1/assess/news-items", json=news_item)
        assert response
        assert response.content_type == "application/json"
        assert response.get_json()["error"] == "not authorized"
        assert response.status_code == 401
        assert before == news_item_data.count_all()

    def test_get_NewsItemAggregates_auth(self, client, news_item, db_session, auth_header):
        """
        This test queries the NewsItemAggregates authenticated.
        It expects a valid data and a valid status-code
        """

        from core.model.news_item import NewsItemAggregate, NewNewsItemDataSchema, NewsItem
        from core.model.osint_source import OSINTSource
        from shared.schema.osint_source import OSINTSourceExportSchema
        from core.model.user import User
        import datetime

        ossi = {
            "description": "",
            "name": "Some Bind",
            "parameter_values": [
                {
                    "value": "https://www.some.bind.it/SiteGlobals/Functions/RSSFeed/RSSNewsfeed/RSSNewsfeed.xml",
                    "parameter": {"key": "FEED_URL"},
                },
            ],
            "collector": {"type": "RSS_COLLECTOR"},
        }

        osint_source = OSINTSourceExportSchema().load(ossi)
        OSINTSource.import_new(osint_source)
        os = OSINTSource.get_all()[0]

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
                "osint_source_id": os.id,
                "published": "2022-02-21T15:01:14.086285",
            },
            {
                "id": "0a129597-592d-45cb-9a80-3218108b29a0",
                "content": "TEST CONTENT XXXX",
                "source": "https: //www.content.xxxx.link/RSSNewsfeed.xml",
                "title": "Bundesinnenministerin Nancy Faeser wird Claudia Plattner zur neuen BSI-Präsidentin berufen",
                "author": "",
                "likes": 0,
                "collected": "2023-01-20T15:00:14.086285",
                "hash": "e270c3a7d87051dea6c3dc14234451f884b427c32791862dacdd7a3e3d318da6",
                "attributes": [],
                "review": "Claudia Plattner wird ab 1. Juli 2023 das Bundesamt für Sicherheitin der Informationstechnik (BSI) leiten.",
                "link": "https: //www.some.other.link/BSI-Praesidentin_230207.html",
                "osint_source_id": os.id,
                "published": "2023-01-20T19:15:00+01:00",
            },
        ]

        news_item_data_schema = NewNewsItemDataSchema(many=True)
        news_items_data = news_item_data_schema.load(news_items_data_list)
        nia = NewsItemAggregate()

        assert news_items_data is not None

        for nid in news_items_data:
            nia.create_new_for_all_groups(nid)

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
