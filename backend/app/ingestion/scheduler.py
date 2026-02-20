"""
Scheduler — builds Celery Beat schedule from insuree configs.
"""


def build_schedule_from_db() -> dict:
    """
    Query all active insurees and build a Celery Beat schedule dict.
    Each insuree's poll_schedule (cron expression) maps to a periodic task.
    """
    raise NotImplementedError("Schedule builder not yet implemented")
