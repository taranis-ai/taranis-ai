from worker.publishers.publisher_tasks import _get_publisher_impl
from worker.publishers.taranis_publisher import TaranisPublisher


def test_taranis_publisher_asks_core_to_store_product(recording_core_api_factory, get_product_mock):
    result_data = {"message": "Product published", "url": "/reports/prod-123"}
    core_api = recording_core_api_factory(put_response=result_data)
    publisher = TaranisPublisher()
    publisher.core_api = core_api

    result = publisher.publish({}, core_api.product, get_product_mock)

    assert result == result_data
    assert core_api.put_calls == [{"url": "/worker/products/prod-123/publish", "json": None}]


def test_taranis_publisher_type_is_registered():
    assert isinstance(_get_publisher_impl("taranis_publisher"), TaranisPublisher)
