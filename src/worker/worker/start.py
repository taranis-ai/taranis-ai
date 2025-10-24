"""
Prefect Worker - Serve flows as deployments

This script serves Prefect flows as deployments so they can be triggered
via run_deployment() from the Core API endpoints.
"""

import os
import sys

try:
    from worker.flows.presenter_task_flow import presenter_task_flow
    from worker.flows.publisher_task_flow import publisher_task_flow
    from worker.flows.connector_task_flow import connector_task_flow
    from worker.flows.bot_task_flow import bot_task_flow
    
    print("Starting Prefect Worker")

    print(f" Prefect API: {os.getenv('PREFECT_API_URL', 'Not set - using default')}")
    print()
    print(" Flows imported successfully:")
    print("  - presenter_task_flow")
    print("  - publisher_task_flow")
    print("  - connector_task_flow")
    print("  - bot_task_flow")
    print()
    
except ImportError as e:
    print(f" ERROR: Failed to import flows: {e}", file=sys.stderr)
    sys.exit(1)


def main():
    from prefect import serve
    
    print(" Serving flows as deployments:")
    print("   - presenter-task-flow/default")
    print("   - publisher-task-flow/default")
    print("   - connector-task-flow/default")
    print("   - bot-task-flow/default")
    print()
    print("⚡ Worker ready - waiting for flow runs...")
    print("=" * 60)
    print()
    
    serve(
        presenter_task_flow.to_deployment(name="default"),
        publisher_task_flow.to_deployment(name="default"),
        connector_task_flow.to_deployment(name="default"),
        bot_task_flow.to_deployment(name="default"),
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n Worker stopped ")
        print("=" * 60)
        sys.exit(0)
    except Exception as e:
        print(f"\n\n Worker failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        print("=" * 60)
        sys.exit(1)