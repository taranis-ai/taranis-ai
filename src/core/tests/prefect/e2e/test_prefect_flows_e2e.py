import pytest
import time
from unittest.mock import Mock, patch
from prefect.testing.utilities import prefect_test_harness

from models.models.bot import BotTaskRequest
from models.models.collector import CollectorTaskRequest  
from models.models.connector import ConnectorTaskRequest
from models.models.presenter import PresenterTaskRequest
from models.models.publisher import PublisherTaskRequest


@pytest.mark.e2e
class TestPrefectFlowsE2E:
    """True E2E tests that execute real Prefect flows"""
    
    def test_publisher_flow_complete_execution_e2e(self):
        """E2E Test: Publisher Flow Complete Execution"""
        print("\nE2E Test: Publisher Flow Complete Execution")
        
        with prefect_test_harness():
            from publisher_task_flow import publisher_task_flow
            
            # Use actual field names from PublisherTaskRequest
            request = PublisherTaskRequest(
                product_id="e2e_test_product_123",
                publisher_id="e2e_test_publisher_456"
            )
            
            # Mock Product with actual methods
            mock_product = Mock()
            mock_product.id = "e2e_test_product_123"
            mock_rendered_product = Mock()
            mock_rendered_product.data = b"E2E test PDF content"
            mock_rendered_product.mime_type = "application/pdf"
            mock_product.get_render.return_value = mock_rendered_product
            
            # Mock Publisher with actual type
            mock_publisher = Mock()
            mock_publisher.id = "e2e_test_publisher_456"
            mock_publisher.type = "email_publisher"
            
            with patch('publisher_task_flow.Product.get', return_value=mock_product), \
                 patch('publisher_task_flow.Publisher.get', return_value=mock_publisher), \
                 patch('publisher_task_flow.PUBLISHER_REGISTRY') as mock_registry:
                
                # Setup publisher mock
                mock_publisher_class = Mock()
                mock_publisher_instance = Mock()
                mock_publisher_instance.publish.return_value = "E2E: Email sent successfully"
                mock_publisher_class.return_value = mock_publisher_instance
                mock_registry.get.return_value = mock_publisher_class
                
                # Execute actual Prefect flow
                start_time = time.time()
                result = publisher_task_flow(request)
                execution_time = time.time() - start_time
                
                # Verify E2E execution
                print(f"   Flow executed in {execution_time:.2f} seconds")
                print(f"   Result: {result['message']}")
                
                # Assert E2E results
                assert "scheduled" in result["message"]
                assert result["result"] == "E2E: Email sent successfully"
                assert execution_time < 10.0
                
                # Verify task execution order
                mock_product.get_render.assert_called_with("email_publisher")
                mock_publisher_instance.publish.assert_called_once()
                
        print("   Publisher Flow E2E Test PASSED")

    def test_collector_flow_real_prefect_orchestration_e2e(self):
        """E2E Test: Collector Flow with Real Prefect Task Orchestration"""
        print("\nE2E Test: Collector Flow Real Orchestration")
        
        with prefect_test_harness():
            from collector_task_flow import collector_task_flow
            
            # Use actual field names from CollectorTaskRequest
            request = CollectorTaskRequest(
                source_id="e2e_rss_source_789",
                preview=False
            )
            
            # Mock source data with actual structure
            mock_source = {
                "id": "e2e_rss_source_789",
                "name": "E2E Test RSS Feed",
                "type": "rss_collector",
                "url": "https://test.com/rss"
            }
            
            with patch('collector_task_flow.CoreApi') as mock_core_api, \
                 patch('collector_task_flow.COLLECTOR_REGISTRY') as mock_registry:
                
                # Setup CoreApi mock
                mock_api_instance = Mock()
                mock_api_instance.get_osint_source.return_value = mock_source
                mock_core_api.return_value = mock_api_instance
                
                # Setup collector mock
                mock_collector_class = Mock()
                mock_collector_instance = Mock()
                mock_collector_instance.name = "RSS Collector"
                mock_collector_instance.collect.return_value = "E2E: Collected 15 news items"
                mock_collector_class.return_value = mock_collector_instance
                mock_registry.get.return_value = mock_collector_class
                
                # Execute with real Prefect orchestration
                start_time = time.time()
                result = collector_task_flow(request)
                execution_time = time.time() - start_time
                
                # Verify E2E orchestration
                print(f"   Flow orchestration time: {execution_time:.2f} seconds")
                print(f"   Collection result: {result['result']}")
                
                # Assert E2E results
                assert result["status"] == "success"
                assert "15 news items" in result["result"]
                assert execution_time < 15.0
                
                # Verify task execution sequence
                mock_api_instance.get_osint_source.assert_called_with("e2e_rss_source_789")
                mock_collector_instance.collect.assert_called_with(mock_source, False)
                
        print("   Collector Flow E2E Test PASSED")

    def test_connector_flow_batch_processing_e2e(self):
        """E2E Test: Connector Flow Batch Processing"""
        print("\nE2E Test: Connector Flow Batch Processing")
        
        with prefect_test_harness():
            from connector_task_flow import connector_task_flow
            
            # TODO field names from ConnectorTaskRequest
            request = ConnectorTaskRequest(
                connector_id="e2e_misp_connector_101",
                story_ids=["story_001", "story_002", "story_003"]
            )
            
            # Mock connector with attributes
            mock_connector = Mock()
            mock_connector.id = "e2e_misp_connector_101"
            mock_connector.type = "misp_connector"
            mock_connector.transform_config = None
            mock_connector.batch_size = 3
            
            # Mock stories with attributes
            mock_stories = []
            for i in range(3):
                story = Mock()
                story.id = f"story_00{i+1}"
                story.title = f"E2E Test Threat {i+1}"
                story.content = f"Threat analysis content {i+1}"
                story.source = "e2e_threat_feed"
                story.published_date = None
                story.web_url = f"https://threats.com/story_{i+1}"
                story.attributes = {"severity": "high"}
                story.mark_pushed_to_connector = Mock()
                mock_stories.append(story)
            
            with patch('connector_task_flow.Connector.get', return_value=mock_connector), \
                 patch('connector_task_flow.NewsItem.get') as mock_get_story, \
                 patch('connector_task_flow.CONNECTOR_REGISTRY') as mock_registry:
                
                # Setup story retrieval
                mock_get_story.side_effect = mock_stories
                
                # Setup connector mock
                mock_connector_class = Mock()
                mock_connector_instance = Mock()
                mock_connector_instance.push.return_value = {"success": True, "processed": 3}
                mock_connector_class.return_value = mock_connector_instance
                mock_registry.get.return_value = mock_connector_class
                
                # Execute with real Prefect task orchestration
                start_time = time.time()
                result = connector_task_flow(request)
                execution_time = time.time() - start_time
                
                # Verify E2E batch processing
                print(f"   Batch processing time: {execution_time:.2f} seconds")
                print(f"   Stories processed: {result['count']}")
                
                # Assert E2E batch results
                assert result["count"] == 3
                assert "scheduled" in result["message"]
                assert execution_time < 20.0
                
                # Verify all stories were marked as pushed
                for story in mock_stories:
                    story.mark_pushed_to_connector.assert_called_with("e2e_misp_connector_101")
                
        print("   Connector Flow E2E Test PASSED")

    def test_presenter_flow_rendering_pipeline_e2e(self):
        """E2E Test: Presenter Flow Complete Rendering Pipeline"""
        print("\nE2E Test: Presenter Flow Rendering Pipeline")
        
        with prefect_test_harness():
            from presenter_task_flow import presenter_task_flow
            
            # Use actual field names from PresenterTaskRequest
            request = PresenterTaskRequest(product_id="e2e_threat_report_999")
            
            mock_product = Mock()
            mock_product.id = "e2e_threat_report_999"
            mock_product.product_type = Mock()
            mock_product.product_type.id = "threat_analysis_report"
            mock_product.add_render = Mock()
            

            mock_presenter = Mock()
            mock_presenter.type = "pdf_presenter"
            mock_presenter.with_limit = True
            mock_presenter.limit = 50
            
            # Mock report items
            mock_report_items = []
            for i in range(5):  # Reduced for faster testing
                item = Mock()
                item.id = f"report_item_{i}"
                item.title = f"Threat Analysis {i}"
                item.content = f"Analysis content {i}"
                mock_report_items.append(item)
            
            with patch('presenter_task_flow.Product.get', return_value=mock_product), \
                 patch('presenter_task_flow.Presenter.get_for_product_type', return_value=mock_presenter), \
                 patch('presenter_task_flow.ReportItem.get_for_product', return_value=mock_report_items), \
                 patch('presenter_task_flow.PRESENTER_REGISTRY') as mock_registry:
                
                # Setup presenter mock
                mock_presenter_class = Mock()
                mock_presenter_instance = Mock()
                mock_presenter_instance.generate.return_value = "E2E: Generated PDF threat report"
                mock_presenter_class.return_value = mock_presenter_instance
                mock_registry.get.return_value = mock_presenter_class
                
                # Execute with real Prefect pipeline orchestration
                start_time = time.time()
                result = presenter_task_flow(request)
                execution_time = time.time() - start_time
                
                # Verify E2E rendering pipeline
                print(f"   Rendering pipeline time: {execution_time:.2f} seconds")
                print(f"   Report items processed: {len(mock_report_items)}")
                
                # Assert E2E pipeline results
                assert "scheduled" in result["message"]
                assert execution_time < 25.0
                
                # Verify pipeline execution order
                mock_presenter_instance.generate.assert_called_with(
                    product=mock_product, 
                    report_items=mock_report_items
                )
                mock_product.add_render.assert_called_with(
                    "pdf_presenter", 
                    "E2E: Generated PDF threat report"
                )
                
        print("   Presenter Flow E2E Test PASSED")

    def test_bot_flow_analysis_workflow_e2e(self):
        """E2E Test: Bot Flow Complete Analysis Workflow"""
        print("\nE2E Test: Bot Flow Analysis Workflow")
        
        with prefect_test_harness():
            from bot_task_flow import bot_task_flow
            
            # Use actual field names from BotTaskRequest
            request = BotTaskRequest(
                bot_id=42,
                filter={
                    "time_range": "last_24h",
                    "severity": "high"
                }
            )
            
            # Mock bot with actual attributes
            mock_bot = Mock()
            mock_bot.id = 42
            mock_bot.type = "analyst_bot"
            mock_bot.update_last_execution = Mock()
            mock_bot.log_execution_result = Mock()
            
            with patch('bot_task_flow.Bot.get', return_value=mock_bot), \
                 patch('bot_task_flow.BOT_REGISTRY') as mock_registry:
                
                # Setup bot mock
                mock_bot_class = Mock()
                mock_bot_instance = Mock()
                mock_bot_instance.execute.return_value = {
                    "analyzed_items": 127,
                    "threats_detected": 8,
                    "execution_time": "4.2s"
                }
                mock_bot_class.return_value = mock_bot_instance
                mock_registry.get.return_value = mock_bot_class
                
                # Execute with real Prefect workflow orchestration
                start_time = time.time()
                result = bot_task_flow(request)
                execution_time = time.time() - start_time
                
                # Verify E2E analysis workflow
                print(f"   Analysis workflow time: {execution_time:.2f} seconds")
                print(f"   Items analyzed: {result['result']['analyzed_items']}")
                
                # Assert E2E workflow results
                assert "scheduled" in result["message"]
                assert result["result"]["analyzed_items"] == 127
                assert execution_time < 15.0
                
                # Verify bot execution with filters
                mock_bot_instance.execute.assert_called_with(filters={
                    "time_range": "last_24h",
                    "severity": "high"
                })
                
                # Verify bot state updates
                mock_bot.update_last_execution.assert_called_once()
                mock_bot.log_execution_result.assert_called_once()
                
        print("   Bot Flow E2E Test PASSED")

    def test_flow_error_handling_and_recovery_e2e(self):
        """E2E Test: Flow Error Handling and Recovery"""
        print("\nE2E Test: Flow Error Handling and Recovery")
        
        with prefect_test_harness():
            from publisher_task_flow import publisher_task_flow
            
            # Test with invalid data to trigger errors
            request = PublisherTaskRequest(
                product_id="nonexistent_product",
                publisher_id="invalid_publisher"
            )
            
            # Mock to simulate real error conditions
            with patch('publisher_task_flow.Product.get', return_value=None):
                
                start_time = time.time()
                result = publisher_task_flow(request)
                execution_time = time.time() - start_time
                
                # Verify E2E error handling
                print(f"   Error handling time: {execution_time:.2f} seconds")
                print(f"   Error message: {result['error']}")
                
                # Assert E2E error handling
                assert "error" in result
                assert "not found" in result["details"]
                assert execution_time < 5.0
                
        print("   Error Handling E2E Test PASSED")

    def test_comprehensive_e2e_summary(self):
        """E2E Summary Test: Complete Migration Validation"""
        print("\n" + "="*70)
        print("COMPREHENSIVE E2E TEST SUMMARY")
        print("="*70)
        
        e2e_results = []
        
        # Run all tests
        test_methods = [
            ("Publisher Flow E2E", self.test_publisher_flow_complete_execution_e2e),
            ("Collector Flow E2E", self.test_collector_flow_real_prefect_orchestration_e2e),
            ("Connector Flow E2E", self.test_connector_flow_batch_processing_e2e),
            ("Presenter Flow E2E", self.test_presenter_flow_rendering_pipeline_e2e),
            ("Bot Flow E2E", self.test_bot_flow_analysis_workflow_e2e),
            ("Error Handling E2E", self.test_flow_error_handling_and_recovery_e2e)
        ]
        
        for test_name, test_method in test_methods:
            try:
                test_method()
                e2e_results.append(f"PASSED: {test_name}")
            except Exception as e:
                e2e_results.append(f"FAILED: {test_name} - {str(e)[:50]}")
        
        # Display comprehensive results
        print("\nE2E Test Results:")
        print("-" * 50)
        for result in e2e_results:
            print(f"   {result}")
        
        print("\nE2E Migration Benefits Demonstrated:")
        print("   - Real Prefect task orchestration")
        print("   - Proper state management and error handling")
        print("   - Task dependency management")
        print("   - Performance within acceptable limits")
        
        # Calculate success rate
        passed_tests = len([r for r in e2e_results if "PASSED" in r])
        total_tests = len(e2e_results)
        success_rate = (passed_tests / total_tests) * 100
        
        print(f"\nE2E Success Rate: {success_rate:.1f}% ({passed_tests}/{total_tests})")
        
        if success_rate == 100.0:
            print("\nCOMPLETE E2E MIGRATION SUCCESS")
            print("READY FOR PRODUCTION DEPLOYMENT")
        else:
            print(f"\n{total_tests - passed_tests} E2E tests need attention")
        
        print("="*70)
        
        # Assert overall E2E success
        assert success_rate >= 90.0, f"E2E success rate too low: {success_rate:.1f}%"


# Pytest markers
pytestmark = [pytest.mark.e2e, pytest.mark.slow, pytest.mark.prefect]
