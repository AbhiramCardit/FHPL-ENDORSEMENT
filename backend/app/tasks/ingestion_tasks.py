"""
Celery tasks — SFTP polling & file ingestion.
"""

from app.tasks import celery_app


@celery_app.task(bind=True, name="app.tasks.ingestion_tasks.poll_sftp_for_insuree")
def poll_sftp_for_insuree(self, insuree_id: str):
    """
    Poll SFTP server for a specific insuree:
    1. Connect to SFTP using stored credentials
    2. List files in watch folder
    3. Check fingerprint to avoid reprocessing
    4. Download new files, upload to S3/MinIO
    5. Create FileIngestionRecord
    6. Dispatch process_file task
    """
    raise NotImplementedError("SFTP polling not yet implemented")
