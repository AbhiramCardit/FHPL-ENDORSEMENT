"""
Celery tasks — TPA API submission with retry logic.
"""

from app.tasks import celery_app


@celery_app.task(
    bind=True,
    name="app.tasks.submission_tasks.submit_endorsement",
    max_retries=5,
    default_retry_delay=60,
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_backoff_max=3600,
    retry_jitter=True,
)
def submit_endorsement(self, endorsement_id: str):
    """
    Submit an endorsement to the TPA API:
    1. Build TPA-specific payload
    2. Send HTTP request
    3. Log request/response to submission_logs
    4. Update endorsement status
    5. Retry on failure with exponential backoff
    """
    raise NotImplementedError("TPA submission not yet implemented")
