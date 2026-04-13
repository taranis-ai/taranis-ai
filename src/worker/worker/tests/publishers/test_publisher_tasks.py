from worker.publishers.publisher_tasks import publisher_task


class DummyPublisher:
    def publish(self, publisher, product, rendered_product):
        return {
            "publisher": publisher,
            "product": product,
            "rendered_product": rendered_product,
        }


def test_publisher_task_uses_string_product_ids(monkeypatch, mock_job):
    seen = {}

    class DummyCoreApi:
        def get_product(self, product_id):
            seen["product_id"] = product_id
            return {"id": product_id, "title": "Example Product"}

        def get_publisher(self, publisher_id):
            seen["publisher_id"] = publisher_id
            return {"id": publisher_id, "type": "email_publisher"}

        def get_product_render(self, product_id):
            seen["render_product_id"] = product_id
            return object()

    monkeypatch.setattr("worker.publishers.publisher_tasks.CoreApi", DummyCoreApi)
    monkeypatch.setattr("worker.publishers.publisher_tasks.get_current_job", lambda: mock_job)
    monkeypatch.setattr("worker.publishers.publisher_tasks._get_publisher_impl", lambda _: DummyPublisher())

    result = publisher_task("prod-123", "pub-1")

    assert seen == {
        "product_id": "prod-123",
        "publisher_id": "pub-1",
        "render_product_id": "prod-123",
    }
    assert result["product"]["id"] == "prod-123"
    assert result["publisher"]["id"] == "pub-1"
