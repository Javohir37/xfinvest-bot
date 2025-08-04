"""Scheduling functionality for net worth tracking."""
import atexit
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime

from db_assets import record_net_worth

logger = logging.getLogger(__name__)


def setup_scheduler():
    """Set up daily recording of net worth."""
    scheduler = BackgroundScheduler()

    # Run every day at midnight
    scheduler.add_job(daily_net_worth_update, 'cron', hour=0, minute=0)

    # Register the shutdown hook
    atexit.register(lambda: scheduler.shutdown())

    # Start the scheduler
    scheduler.start()
    logger.info("Scheduler started for daily net worth tracking")

    return scheduler


def daily_net_worth_update():
    """Daily job to update net worth."""
    today = datetime.now().strftime('%Y-%m-%d')
    logger.info(f"Recording net worth for {today}")

    try:
        record_net_worth(today)
        logger.info("Net worth recorded successfully")
    except Exception as e:
        logger.error(f"Error recording net worth: {e}", exc_info=True)