import sys
import os
import time
from pathlib import Path

# Add paths for imports
current_dir = Path(__file__).parent
worker_path = current_dir.parent.parent
src_path = worker_path.parent.parent / "src"

sys.path.insert(0, str(worker_path))
sys.path.insert(0, str(src_path))

# Set environment for testing
os.environ.setdefault("TESTING", "1")


def run_e2e_tests():
    """Run the comprehensive E2E test suite"""
    print("Taranis AI: Prefect Migration E2E Tests")
    print("=" * 45)
    print("Testing Celery to Prefect migration")
    print("Validating real Prefect flow orchestration")
    print("-" * 45)
    
    try:
        from test_prefect_flows_e2e import TestPrefectFlowsE2E
        
        print("Running comprehensive E2E test suite...")
        start_time = time.time()
        
        test_suite = TestPrefectFlowsE2E()
        test_suite.test_comprehensive_e2e_summary()
        
        execution_time = time.time() - start_time
        print(f"\nTotal execution time: {execution_time:.2f} seconds")
        print("E2E tests completed successfully!")
        print("Migration validation: PASSED")
        return True
        
    except ImportError as e:
        print(f"Import error: {e}")
        print("Make sure you're running from: src/worker/worker/tests/e2e/")
        return False
        
    except Exception as e:
        print(f"E2E tests failed: {e}")
        return False


def main():
    """Main entry point"""
    if not Path("test_prefect_flows_e2e.py").exists():
        print("Error: test_prefect_flows_e2e.py not found")
        print("Please run from: src/worker/worker/tests/e2e/")
        return False
    
    return run_e2e_tests()

