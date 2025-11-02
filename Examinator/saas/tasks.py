from celery import shared_task
from django.core.management import call_command
import logging

logger = logging.getLogger(__name__)

# This task is designed to be executed periodically by Celery Beat.
# It removes the headache of external scheduling by running your logic
# internally, managed by your Django project database.
@shared_task
def sync_expired_licenses_task():
    """
    Runs the license synchronization management command to check for
    and revoke access/permissions for expired licenses.
    """
    logger.info("Starting scheduled license synchronization via Celery Beat.")
    try:
        # 'sync_expired_licenses' is the name of your management command file (without .py)
        # verbosity=1 ensures it logs the progress messages you added to the command.
        call_command('sync_expired_licenses', verbosity=1)
        logger.info("License synchronization completed successfully.")
        return "License synchronization completed successfully."
    except Exception as e:
        logger.error(f"License synchronization failed: {e}")
        # Re-raise for Celery to mark the task as failed
        raise
