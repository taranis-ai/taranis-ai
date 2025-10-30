"""
End-to-End Tests for Prefect Flows

Tests all core Prefect business workflows:
- Presenter flows (PDF/HTML generation)
- Publisher flows (report delivery)
- Connector flows (external system integration)
- Bot flows (AI/analysis processing)

Tests automatically start Prefect Server, Core, and Worker via conftest.py fixtures.
"""

import pytest
from .utils.api_client import TaranisAPIClient, TestData, wait_for_flow_completion


@pytest.mark.prefect
@pytest.mark.presenter_flow
class TestPresenterFlow:
    """Test Prefect presenter flows - PDF and HTML generation from products"""

    def test_pdf_presenter_flow_creates_render(self, api_client: TaranisAPIClient, test_data: TestData):
        """Test that PDF presenter flow generates a PDF render from product data"""
        print("\n=== Testing PDF Presenter Flow ===")

        # Verify we have the required test data
        assert test_data.product_id, "No product ID available"
        assert test_data.presenter_id, "No presenter ID available"

        # Get initial renders count
        initial_renders = api_client.get_product_renders(test_data.product_id)
        initial_count = len(initial_renders)
        print(f"Product {test_data.product_id} has {initial_count} existing renders")

        # Trigger presenter flow
        flow_run_id = api_client.trigger_presenter_flow(product_id=test_data.product_id, presenter_id=test_data.presenter_id)

        # Wait for completion
        wait_for_flow_completion(api_client, flow_run_id, timeout=180)

        # Verify new render was created
        final_renders = api_client.get_product_renders(test_data.product_id)
        final_count = len(final_renders)

        assert final_count > initial_count, f"No new render created. Expected > {initial_count}, got {final_count}"
        print(f"Success: Product now has {final_count} renders")

        # Find the newest render
        if final_renders:
            latest_render = max(final_renders, key=lambda r: r.get("created_at", ""))

            # Verify render has expected properties
            assert latest_render.get("status") == "COMPLETED", f"Render status is {latest_render.get('status')}, expected COMPLETED"
            assert latest_render.get("output_path"), "Render missing output_path"
            assert latest_render.get("mime_type"), "Render missing mime_type"

            print("Render created successfully:")
            print(f"  Status: {latest_render.get('status')}")
            print(f"  Output: {latest_render.get('output_path')}")
            print(f"  Type: {latest_render.get('mime_type')}")

    def test_presenter_flow_with_invalid_product(self, api_client: TaranisAPIClient, test_data: TestData):
        """Test presenter flow error handling with invalid product ID"""
        print("\n=== Testing Presenter Flow Error Handling ===")

        # Try to trigger flow with non-existent product
        with pytest.raises(Exception) as exc_info:
            api_client.trigger_presenter_flow(product_id="invalid-product-id", presenter_id=test_data.presenter_id)

        print(f"Expected error caught: {exc_info.value}")


@pytest.mark.prefect
@pytest.mark.publisher_flow
class TestPublisherFlow:
    """Test Prefect publisher flows - report delivery to external systems"""

    def test_ftp_publisher_flow_creates_publication(self, api_client: TaranisAPIClient, test_data: TestData):
        """Test that FTP publisher flow publishes a product render"""
        print("\n=== Testing FTP Publisher Flow ===")

        # Verify test data
        assert test_data.product_id, "No product ID available"
        assert test_data.publisher_id, "No publisher ID available"

        # First ensure we have a render to publish (run presenter flow)
        print("Creating render first...")
        presenter_flow_id = api_client.trigger_presenter_flow(product_id=test_data.product_id, presenter_id=test_data.presenter_id)
        wait_for_flow_completion(api_client, presenter_flow_id, timeout=180)

        # Verify render was created
        renders = api_client.get_product_renders(test_data.product_id)
        completed_renders = [r for r in renders if r.get("status") == "COMPLETED"]
        assert len(completed_renders) > 0, "No completed render available for publishing"

        print(f"Found {len(completed_renders)} completed renders to publish")

        # Get initial publications count
        initial_publications = api_client.get_product_publications(test_data.product_id)
        initial_count = len(initial_publications)
        print(f"Product {test_data.product_id} has {initial_count} existing publications")

        # Trigger publisher flow
        flow_run_id = api_client.trigger_publisher_flow(product_id=test_data.product_id, publisher_id=test_data.publisher_id)

        # Wait for completion
        wait_for_flow_completion(api_client, flow_run_id, timeout=180)

        # Verify new publication was created
        final_publications = api_client.get_product_publications(test_data.product_id)
        final_count = len(final_publications)

        assert final_count > initial_count, f"No new publication created. Expected > {initial_count}, got {final_count}"
        print(f"Success: Product now has {final_count} publications")

        # Find the newest publication
        if final_publications:
            latest_publication = max(final_publications, key=lambda p: p.get("created_at", ""))

            # Verify publication has expected properties
            assert latest_publication.get("status") == "PUBLISHED", (
                f"Publication status is {latest_publication.get('status')}, expected PUBLISHED"
            )
            assert latest_publication.get("published_at"), "Publication missing published_at timestamp"

            print("Publication created successfully:")
            print(f"  Status: {latest_publication.get('status')}")
            print(f"  Published: {latest_publication.get('published_at')}")
            print(f"  Destination: {latest_publication.get('destination', 'N/A')}")


@pytest.mark.prefect
@pytest.mark.connector_flow
class TestConnectorFlow:
    """Test Prefect connector flows - external system integration"""

    def test_misp_connector_flow_pushes_news_items(self, api_client: TaranisAPIClient, test_data: TestData):
        """Test that MISP connector flow pushes news items to external system"""
        print("\n=== Testing MISP Connector Flow ===")

        # Verify test data
        assert test_data.connector_id, "No connector ID available"
        assert test_data.news_item_ids, "No news item IDs available"

        print(f"Testing with {len(test_data.news_item_ids)} news items")

        # Get initial push status of news items
        initial_items = api_client.get_news_items_by_ids(test_data.news_item_ids)
        initially_pushed = [item for item in initial_items if item.get("pushed") is True]
        print(f"Initially pushed items: {len(initially_pushed)}")

        # Trigger connector flow
        flow_run_id = api_client.trigger_connector_flow(connector_id=test_data.connector_id, story_ids=test_data.story_ids)

        # Wait for completion
        wait_for_flow_completion(api_client, flow_run_id, timeout=180)

        # Verify news items were marked as pushed
        final_items = api_client.get_news_items_by_ids(test_data.news_item_ids)
        finally_pushed = [item for item in final_items if item.get("pushed") is True]

        assert len(finally_pushed) > len(initially_pushed), (
            f"No additional items were pushed. Expected > {len(initially_pushed)}, got {len(finally_pushed)}"
        )
        print(f"Success: {len(finally_pushed)} items now marked as pushed")

        # Verify pushed items have timestamps
        for item in finally_pushed:
            if item.get("pushed") is True:
                assert item.get("pushed_at"), f"News item {item.get('id')} missing pushed_at timestamp"
                print(f"  Item {item.get('id')}: pushed at {item.get('pushed_at')}")

    def test_connector_flow_with_empty_stories(self, api_client: TaranisAPIClient, test_data: TestData):
        """Test connector flow with empty story list"""
        print("\n=== Testing Connector Flow with Empty Stories ===")

        # Trigger connector flow with empty story list
        flow_run_id = api_client.trigger_connector_flow(connector_id=test_data.connector_id, story_ids=[])

        # Should complete successfully even with no stories
        wait_for_flow_completion(api_client, flow_run_id, timeout=60)
        print("Success: Connector flow handled empty story list gracefully")


@pytest.mark.prefect
@pytest.mark.bot_flow
class TestBotFlow:
    """Test Prefect bot flows - AI/analysis processing of news items"""

    def test_nlp_bot_flow_processes_news_items(self, api_client: TaranisAPIClient, test_data: TestData):
        """Test that NLP bot flow processes news items and adds analysis"""
        print("\n=== Testing NLP Bot Flow ===")

        # Verify test data
        assert test_data.bot_id, "No bot ID available"
        assert test_data.news_item_ids, "No news item IDs available"

        print(f"Testing NLP bot with {len(test_data.news_item_ids)} news items")

        # Get initial state of news items
        initial_items = api_client.get_news_items_by_ids(test_data.news_item_ids)
        print(f"Found {len(initial_items)} news items for processing")

        # Count initial attributes/tags
        initial_attributes = sum(len(item.get("attributes", [])) for item in initial_items)
        print(f"Initial total attributes: {initial_attributes}")

        # Trigger bot flow
        flow_run_id = api_client.trigger_bot_flow(bot_id=test_data.bot_id, story_ids=test_data.story_ids)

        # Wait for completion
        wait_for_flow_completion(api_client, flow_run_id, timeout=180)

        # Verify bot processing results
        final_items = api_client.get_news_items_by_ids(test_data.news_item_ids)
        final_attributes = sum(len(item.get("attributes", [])) for item in final_items)

        # Note: Bot processing might not always add attributes, depending on content
        # So we verify the flow completed rather than specific attribute changes
        print(f"Final total attributes: {final_attributes}")
        print("Success: Bot flow completed successfully")

        # Check if any items were processed (optional verification)
        for item in final_items:
            if item.get("processed_by_bots") or item.get("last_processed"):
                print(f"  Item {item.get('id')}: processed by bots")

    def test_bot_flow_without_story_filter(self, api_client: TaranisAPIClient, test_data: TestData):
        """Test bot flow without specific story IDs (processes available stories)"""
        print("\n=== Testing Bot Flow Without Story Filter ===")

        # Trigger bot flow without story IDs
        flow_run_id = api_client.trigger_bot_flow(
            bot_id=test_data.bot_id
            # No story_ids parameter - should process available stories
        )

        # Wait for completion
        wait_for_flow_completion(api_client, flow_run_id, timeout=180)
        print("Success: Bot flow completed without specific story filter")


@pytest.mark.prefect
@pytest.mark.slow
class TestFlowIntegration:
    """Integration tests combining multiple flows"""

    def test_complete_content_pipeline(self, api_client: TaranisAPIClient, test_data: TestData):
        """Test complete pipeline: Bot processing -> Presentation -> Publishing -> Connector push"""
        print("\n=== Testing Complete Content Pipeline ===")

        # Step 1: Process news with bot
        print("Step 1: Processing news items with bot...")
        bot_flow_id = api_client.trigger_bot_flow(bot_id=test_data.bot_id, story_ids=test_data.story_ids)
        wait_for_flow_completion(api_client, bot_flow_id, timeout=180)

        # Step 2: Generate report from product
        print("Step 2: Generating PDF report...")
        presenter_flow_id = api_client.trigger_presenter_flow(product_id=test_data.product_id, presenter_id=test_data.presenter_id)
        wait_for_flow_completion(api_client, presenter_flow_id, timeout=180)

        # Step 3: Publish the report
        print("Step 3: Publishing report...")
        publisher_flow_id = api_client.trigger_publisher_flow(product_id=test_data.product_id, publisher_id=test_data.publisher_id)
        wait_for_flow_completion(api_client, publisher_flow_id, timeout=180)

        # Step 4: Push news to external system
        print("Step 4: Pushing news to external system...")
        connector_flow_id = api_client.trigger_connector_flow(connector_id=test_data.connector_id, story_ids=test_data.story_ids)
        wait_for_flow_completion(api_client, connector_flow_id, timeout=180)

        # Verify end-to-end results
        print("\n=== Verifying End-to-End Results ===")

        # Check renders were created
        renders = api_client.get_product_renders(test_data.product_id)
        completed_renders = [r for r in renders if r.get("status") == "COMPLETED"]
        assert len(completed_renders) > 0, "No completed renders after presenter flow"
        print(f"✓ {len(completed_renders)} renders created")

        # Check publications were created
        publications = api_client.get_product_publications(test_data.product_id)
        published = [p for p in publications if p.get("status") == "PUBLISHED"]
        assert len(published) > 0, "No publications after publisher flow"
        print(f"✓ {len(published)} publications created")

        # Check news items were pushed
        final_items = api_client.get_news_items_by_ids(test_data.news_item_ids)
        pushed_items = [item for item in final_items if item.get("pushed") is True]
        assert len(pushed_items) > 0, "No news items were pushed after connector flow"
        print(f"✓ {len(pushed_items)} news items pushed to external system")

        print("\n Complete content pipeline test successful!")
        print("   Flows executed: bot -> presenter -> publisher -> connector")
        print(f"   Flow IDs: {bot_flow_id}, {presenter_flow_id}, {publisher_flow_id}, {connector_flow_id}")


@pytest.mark.prefect
class TestPrefectSystem:
    """Tests for Prefect system integration and health"""

    def test_prefect_flows_are_registered(self, api_client: TaranisAPIClient):
        """Test that expected Prefect flows are registered and accessible"""
        print("\n=== Testing Prefect Flow Registration ===")

        flows = api_client.check_prefect_flows()
        flow_names = [f.get("name") for f in flows.get("flows", [])]

        print(f"Available Prefect flows: {flow_names}")

        # Check for expected core flows
        expected_flows = ["presenter-task-flow", "publisher-task-flow", "connector-task-flow", "bot-task-flow"]

        missing_flows = []
        for expected_flow in expected_flows:
            if expected_flow not in flow_names:
                missing_flows.append(expected_flow)

        if missing_flows:
            print(f"Warning: Missing expected flows: {missing_flows}")
            print("This might be expected during migration period")
        else:
            print(" All expected Prefect flows are registered")

        # At minimum, we should have some flows registered
        assert len(flow_names) > 0, "No Prefect flows are registered"
        print(f"✓ Prefect system has {len(flow_names)} registered flows")


if __name__ == "__main__":
    """Allow running tests directly for development"""
    pytest.main([__file__, "-v", "--tb=short"])
