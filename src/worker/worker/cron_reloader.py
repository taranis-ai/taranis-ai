"""Cron job reload mechanism using Redis pub/sub

This module provides real-time configuration reloading for the RQ cron scheduler
when OSINT source or bot schedules change.
"""
import threading
from redis import Redis
from worker.log import logger
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rq.cron import CronScheduler


CRON_CONFIG_CHANNEL = "taranis:cron:reload"


class CronReloader:
    """Listens for config changes and reloads cron scheduler jobs"""
    
    def __init__(self, scheduler: 'CronScheduler', redis_conn: Redis):
        self.scheduler = scheduler
        self.redis_conn = redis_conn
        self.pubsub = redis_conn.pubsub()
        self.listener_thread = None
        self._stop_event = threading.Event()
        
    def start(self):
        """Start listening for reload signals"""
        self.pubsub.subscribe(CRON_CONFIG_CHANNEL)
        logger.info(f"CronReloader: subscribed to {CRON_CONFIG_CHANNEL}")
        
        self.listener_thread = threading.Thread(
            target=self._listen_for_changes,
            daemon=True,
            name="CronReloader"
        )
        self.listener_thread.start()
        
    def stop(self):
        """Stop listening"""
        self._stop_event.set()
        self.pubsub.unsubscribe(CRON_CONFIG_CHANNEL)
        self.pubsub.close()
        if self.listener_thread:
            self.listener_thread.join(timeout=5)
        logger.info("CronReloader: stopped")
        
    def _listen_for_changes(self):
        """Listen for pub/sub messages and reload config"""
        logger.info("CronReloader: listener thread started")
        
        for message in self.pubsub.listen():
            if self._stop_event.is_set():
                break
                
            if message['type'] == 'message':
                data = message['data']
                if isinstance(data, bytes):
                    data = data.decode('utf-8')
                    
                logger.info(f"CronReloader: received reload signal: {data}")
                self._reload_jobs()
                
    def _reload_jobs(self):
        """Reload all cron jobs from database"""
        try:
            logger.info("CronReloader: clearing existing jobs...")
            
            # Clear existing jobs
            self.scheduler._cron_jobs.clear()
            
            # Reload from database
            logger.info("CronReloader: reloading jobs from database...")
            from worker.cron_config import load_cron_jobs
            load_cron_jobs(self.scheduler)
            
            logger.info("CronReloader: reload complete")
            
        except Exception as e:
            logger.exception(f"CronReloader: failed to reload jobs: {e}")


def publish_reload_signal(redis_conn: Redis, reason: str = "config_changed"):
    """Publish a signal to reload cron configuration
    
    Args:
        redis_conn: Redis connection
        reason: Reason for reload (for logging)
    """
    try:
        redis_conn.publish(CRON_CONFIG_CHANNEL, reason)
        logger.info(f"Published cron reload signal: {reason}")
    except Exception as e:
        logger.error(f"Failed to publish reload signal: {e}")
