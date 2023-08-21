import pytest


@pytest.fixture(scope="function")
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
            "collector_type": "RSS_COLLECTOR",
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
        nia1 = nia.create_new(news_items_data[0])
        nia2 = nia.create_new(news_items_data[1])

        def teardown():
            nia = NewsItemAggregate()
            user = User.find_by_name("admin")
            news_item_aggregates, _ = nia.get_by_filter({"group": "default"}, user)
            for aggregate in news_item_aggregates:
                aggregate.delete(user)

        request.addfinalizer(teardown)

        yield [nia1, nia2]


@pytest.fixture(scope="session")
def cleanup_sources(app, request):
    with app.app_context():
        from core.model.osint_source import OSINTSource

        def teardown():
            with app.app_context():
                [OSINTSource.delete(source.id) for source in OSINTSource.get_all()]

        request.addfinalizer(teardown)


@pytest.fixture(scope="session")
def cleanup_word_lists(app, request):
    with app.app_context():
        from core.model.word_list import WordList

        def teardown():
            with app.app_context():
                [WordList.delete(source.id) for source in WordList.get_all()]

        request.addfinalizer(teardown)


@pytest.fixture(scope="session")
def cleanup_user(app, request):
    with app.app_context():
        from core.model.user import User

        user_data = {
            "id": 42,
            "username": "testuser",
            "name": "Test User",
            "organization": 1,
            "roles": [2],
            "permissions": ["ANALYZE_ACCESS", "ANALYZE_CREATE", "ANALYZE_DELETE"],
            "password": "testpassword",
        }

        def teardown():
            with app.app_context():
                if User.get(42):
                    print("Deleting test user 42")
                    User.delete(42)

        request.addfinalizer(teardown)

        yield user_data


@pytest.fixture(scope="session")
def cleanup_role(app, request):
    with app.app_context():
        from core.model.role import Role

        role_data = {
            "id": 42,
            "name": "testrole",
            "description": "Test Role",
            "permissions": ["ANALYZE_ACCESS", "ANALYZE_CREATE", "ANALYZE_DELETE"],
        }

        def teardown():
            with app.app_context():
                if Role.get(42):
                    print("Deleting test user 42")
                    Role.delete(42)

        request.addfinalizer(teardown)

        yield role_data
