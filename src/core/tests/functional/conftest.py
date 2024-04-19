import pytest


@pytest.fixture(scope="session")
def fake_source(app, request):
    with app.app_context():
        from core.model.osint_source import OSINTSource

        source_data = {
            "id": "99",
            "description": "This is a test source",
            "name": "Test Source",
            "parameters": [
                {"FEED_URL": "https://url/feed.xml"},
            ],
            "type": "rss_collector",
        }
        source_id = source_data["id"]

        if not OSINTSource.get(source_id):
            OSINTSource.add(source_data)

        def teardown():
            with app.app_context():
                OSINTSource.delete(source_id)

        request.addfinalizer(teardown)

        yield source_id


@pytest.fixture(scope="session")
def news_items_data(app, fake_source):
    with app.app_context():
        from core.model.news_item import NewsItem

        news_items_list = [
            {
                "id": "1be00eef-6ade-4818-acfc-25029531a9a5",
                "content": "TEST CONTENT YYYY",
                "source": "https: //www.some.link/RSSNewsfeed.xml",
                "title": "Mobile World Congress 2023",
                "author": "",
                "collected": "2022-02-21T15:00:14.086285",
                "hash": "82e6e99403686a1072d0fb2013901b843a6725ba8ac4266270f62b7614ec1adf",
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
                "review": "Claudia Plattner wird ab 1. Juli 2023 das Bundesamt für Sicherheitin der Informationstechnik (BSI) leiten.",
                "link": "https: //www.some.other.link/BSI-Praesidentin_230207.html",
                "osint_source_id": fake_source,
                "published": "2023-01-20T19:15:00+01:00",
            },
        ]

        yield NewsItem.load_multiple(news_items_list)


@pytest.fixture(scope="session")
def stories(app, request, news_items_data):
    with app.app_context():
        from core.model.story import Story
        from core.model.report_item import ReportItem

        nia1 = Story.add(news_items_data[0])
        nia2 = Story.add(news_items_data[1])

        def teardown():
            with app.app_context():
                ReportItem.delete_all()
                Story.delete_all()

        request.addfinalizer(teardown)

        yield [nia1, nia2]


@pytest.fixture(scope="session")
def cleanup_report_item(app, request):
    with app.app_context():
        from core.model.report_item import ReportItem
        from core.model.report_item_type import ReportItemType

        first_report_type = ReportItemType.get_all()[0].id

        report_data = {
            "id": "42",
            "title": "Test Report",
            "completed": False,
            "report_item_type_id": first_report_type,
            "stories": [],
        }

        def teardown():
            with app.app_context():
                ReportItem.delete_all()

        request.addfinalizer(teardown)

        yield report_data


@pytest.fixture(scope="session")
def cleanup_product(app, request):
    with app.app_context():
        from core.model.product import Product
        from core.model.product_type import ProductType
        from core.model.worker import PRESENTER_TYPES

        text_presenter = ProductType.get_by_type(PRESENTER_TYPES.TEXT_PRESENTER)
        if not text_presenter:
            raise ValueError("No text presenter found")

        product_data = {
            "id": "42",
            "title": "Test Product",
            "description": "This is a test product",
            "product_type_id": text_presenter.id,
        }

        def teardown():
            with app.app_context():
                Product.delete_all()

        request.addfinalizer(teardown)

        yield product_data
