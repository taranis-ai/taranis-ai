import pytest
from worker.flows.gather_word_list import gather_word_list_flow, gather_word_list_simple, WordListTaskRequest


class TestGatherWordListFlowE2E:
    """Essential E2E tests for gather word list flow"""
    
    def test_wordlist_flow_success(self, mock_core_api, mock_requests, sample_wordlist_request):
        """Test successful word list gathering - matches original Celery behavior"""
        # Arrange
        mock_core_api.get_word_list.return_value = {
            "id": 1,
            "name": "Test Wordlist",
            "link": "https://example.com/wordlist.txt"
        }
        
        # Act
        result = gather_word_list_flow(sample_wordlist_request)
        
        # Assert
        assert result is not None
        assert result["word_list_id"] == 1
        assert "content" in result
        assert "content_type" in result
        mock_core_api.get_word_list.assert_called_once_with(1)
        mock_requests.assert_called_once_with(url="https://example.com/wordlist.txt", timeout=60)
    
    def test_wordlist_simple_flow_success(self, mock_core_api, mock_requests):
        """Test simple word list flow - direct function call like original"""
        # Arrange
        mock_core_api.get_word_list.return_value = {
            "id": 1,
            "name": "Test Wordlist", 
            "link": "https://example.com/wordlist.txt"
        }
        
        # Act
        result = gather_word_list_simple(1)
        
        # Assert
        assert result is not None
        assert result["word_list_id"] == 1
    
    def test_wordlist_flow_word_list_not_found(self, mock_core_api, sample_wordlist_request):
        """Test word list not found error"""
        # Arrange
        mock_core_api.get_word_list.return_value = None
        
        # Act & Assert
        with pytest.raises(RuntimeError, match="Word list with id .* not found"):
            gather_word_list_flow(sample_wordlist_request)
    
    def test_wordlist_flow_download_failure(self, mock_core_api, mock_requests, sample_wordlist_request):
        """Test download failure handling"""
        # Arrange
        mock_core_api.get_word_list.return_value = {
            "id": 1,
            "name": "Test Wordlist",
            "link": "https://example.com/wordlist.txt"
        }
        mock_requests.return_value.ok = False
        mock_requests.return_value.status_code = 404
        
        # Act & Assert
        with pytest.raises(RuntimeError, match="Failed to download word list"):
            gather_word_list_flow(sample_wordlist_request)
    
    def test_wordlist_flow_content_type_detection(self, mock_core_api, mock_requests, sample_wordlist_request):
        """Test content type detection - matches original Celery behavior"""
        # Arrange
        mock_core_api.get_word_list.return_value = {
            "id": 1,
            "name": "Test Wordlist",
            "link": "https://example.com/wordlist.csv"
        }
        mock_requests.return_value.headers = {"content-type": "text/csv"}
        mock_requests.return_value.text = "word1,category1\nword2,category2"
        
        # Act
        result = gather_word_list_flow(sample_wordlist_request)
        
        # Assert
        assert result["content_type"] == "text/csv"
        assert result["content"] == "word1,category1\nword2,category2"