from worker.publishers.execution_context import PublisherExecutionContext


def test_execution_context_caps_network_timeout(recording_job_factory):
    job = recording_job_factory(timeout=40)
    context = PublisherExecutionContext(product_id="product-1", publisher_id="publisher-1", job=job)

    assert context.effective_network_timeout(30) == 20
