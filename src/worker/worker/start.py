"""
Prefect Worker Process for E2E Testing

This script imports all Prefect flows so they're available for execution.
The worker process stays alive and Prefect Server can execute flows via .submit()
"""

import time
import sys

# Import all Prefect flows to register them
try:
    from worker.flows.presenter_task_flow import presenter_task_flow  # noqa: F401
    from worker.flows.publisher_task_flow import publisher_task_flow  # noqa: F401
    from worker.flows.connector_task_flow import connector_task_flow  # noqa: F401
    from worker.flows.bot_task_flow import bot_task_flow              # noqa: F401
    
    print("[worker] Prefect flows loaded successfully:")
    print("  ✓ presenter_task_flow")
    print("  ✓ publisher_task_flow")
    print("  ✓ connector_task_flow")
    print("  ✓ bot_task_flow")
    print("[worker] Ready for flow execution...")
    
except ImportError as e:
    print(f"[worker] ERROR: Failed to import flows: {e}", file=sys.stderr)
    sys.exit(1)


def main():
    """
    Keep the worker process alive so Prefect can execute flows.
    When Core calls flow.submit(), Prefect Server will execute the flow.
    """
    try:
        while True:
            time.sleep(5)  # Just stay alive
    except KeyboardInterrupt:
        print("\n[worker] Shutting down...")
        sys.exit(0)


if __name__ == "__main__":
    main()