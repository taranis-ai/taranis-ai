import threading
import asyncio
from flask import Flask
from apscheduler.schedulers.asyncio import AsyncIOScheduler

app = Flask(__name__)


def debug_job():
    print("Debug job running")


def run_scheduler():
    # Create a new event loop for this thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Initialize and start the AsyncIOScheduler with the new event loop
    scheduler = AsyncIOScheduler(event_loop=loop)
    scheduler.add_job(debug_job, "interval", seconds=5)
    scheduler.start()

    # Run the event loop forever
    loop.run_forever()


if __name__ == "__main__":
    # Start the scheduler in a separate thread
    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.start()

    # Run the Flask application
    app.run(debug=True, use_reloader=False)
