"""RQ Worker for Taranis AI

This module sets up RQ workers for different job types:
- collectors: Collect news from OSINT sources
- bots: Process news items with bots
- presenters: Generate products/reports
- publishers: Publish products to external systems
- connectors: Handle external integrations

Usage:
    rq worker collectors bots presenters publishers connectors
"""
import sys
import redis
from rq import Worker, Queue

from worker.config import Config
from worker.core_api import CoreApi
from worker.log import logger


def get_redis_connection():
    """Get Redis connection from config."""
    return redis.from_url(
        Config.REDIS_URL,
        password=Config.REDIS_PASSWORD,
        decode_responses=False,
    )


def get_queues():
    """Get list of queue names based on configured worker types."""
    queue_names = []
    worker_types = Config.WORKER_TYPES
    
    if "Collectors" in worker_types:
        queue_names.append("collectors")
    if "Bots" in worker_types:
        queue_names.append("bots")
    if "Presenters" in worker_types:
        queue_names.append("presenters")
    if "Publishers" in worker_types:
        queue_names.append("publishers")
    if "Connectors" in worker_types:
        queue_names.append("connectors")
    
    return queue_names


def start_worker():
    """Start RQ worker with configured queues."""
    # Initialize core API for worker tasks to use
    CoreApi()
    
    # Import task modules to register functions
    from worker.tasks import register_tasks
    register_tasks()
    
    # Get Redis connection
    redis_conn = get_redis_connection()
    
    # Get queue names
    queue_names = get_queues()
    if not queue_names:
        logger.error("No worker types configured. Set WORKER_TYPES in config.")
        sys.exit(1)
    
    # Create Queue objects
    queues = [Queue(name, connection=redis_conn) for name in queue_names]
    
    logger.info(f"Starting RQ worker for queues: {', '.join(queue_names)}")
    
    # Start worker
    worker = Worker(queues, connection=redis_conn)
    worker.work(with_scheduler=True)


if __name__ == "__main__":
    start_worker()
