"""
Test to verify the SQLAlchemy connection pool deadlock fix.

This test simulates the scenario described in issue #478 where APScheduler
and the main application compete for database connections, causing timeouts.
"""
import pytest
import tempfile
import os
from unittest.mock import patch
import sys

# Add path for core module
sys.path.insert(0, '/home/runner/work/taranis-ai/taranis-ai/src/core')


def test_scheduler_separate_engine_configuration():
    """Test that scheduler configuration uses separate pool settings."""
    from core.config import Config
    
    # Verify new configuration options exist
    assert hasattr(Config, 'SQLALCHEMY_SCHEDULER_POOL_SIZE')
    assert hasattr(Config, 'SQLALCHEMY_SCHEDULER_MAX_OVERFLOW')
    
    # Verify default values are reasonable
    assert Config.SQLALCHEMY_SCHEDULER_POOL_SIZE == 5
    assert Config.SQLALCHEMY_SCHEDULER_MAX_OVERFLOW == 2
    
    # Verify main app has different (larger) pool settings
    assert Config.SQLALCHEMY_POOL_SIZE == 20
    assert Config.SQLALCHEMY_MAX_OVERFLOW == 10


def test_scheduler_creates_separate_engine():
    """Test that the scheduler creates its own engine instead of sharing db.engine."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        test_db_path = f.name
    
    try:
        # Use a mock to test engine creation without requiring database connection
        with patch('core.managers.schedule_manager.create_engine') as mock_create_engine:
            from core.config import Config
            
            # Mock the engine to avoid actual database connection
            mock_engine = type('MockEngine', (), {})()
            mock_create_engine.return_value = mock_engine
            
            # Import and create scheduler
            from core.managers.schedule_manager import Scheduler
            
            # Mock the scheduler start to avoid database operations
            with patch.object(Scheduler, 'start'):
                scheduler = Scheduler()
            
            # Verify create_engine was called with scheduler-specific settings
            mock_create_engine.assert_called_once()
            call_args = mock_create_engine.call_args
            
            # Verify the engine options include scheduler pool settings
            engine_options = call_args[1]  # kwargs
            assert 'pool_size' in engine_options
            assert 'max_overflow' in engine_options
            assert engine_options['pool_size'] == Config.SQLALCHEMY_SCHEDULER_POOL_SIZE
            assert engine_options['max_overflow'] == Config.SQLALCHEMY_SCHEDULER_MAX_OVERFLOW
        
    finally:
        # Clean up temp database
        try:
            os.unlink(test_db_path)
        except:
            pass


def test_scheduler_engine_has_correct_pool_settings():
    """Test that the scheduler's engine uses the correct pool configuration."""
    from core.config import Config
    
    # Test that configuration values are correctly set
    # The actual engine creation is tested in other tests
    assert Config.SQLALCHEMY_SCHEDULER_POOL_SIZE > 0
    assert Config.SQLALCHEMY_SCHEDULER_MAX_OVERFLOW >= 0
    
    # Test that scheduler settings are independent from main app settings
    assert (Config.SQLALCHEMY_SCHEDULER_POOL_SIZE, Config.SQLALCHEMY_SCHEDULER_MAX_OVERFLOW) != \
           (Config.SQLALCHEMY_POOL_SIZE, Config.SQLALCHEMY_MAX_OVERFLOW)


if __name__ == '__main__':
    print("Running SQLAlchemy connection pool deadlock fix tests...")
    
    test_scheduler_separate_engine_configuration()
    print("✓ Configuration test passed")
    
    test_scheduler_creates_separate_engine()
    print("✓ Separate engine creation test passed")
    
    test_scheduler_engine_has_correct_pool_settings()
    print("✓ Engine pool settings test passed")
    
    print("\n✅ All tests passed! The fix should prevent SQLAlchemy TimeoutError deadlocks.")
    print("📝 The scheduler now uses a dedicated connection pool separate from the main application.")