"""
Celery tasks — document processing pipeline.
"""

from app.tasks import celery_app


@celery_app.task(bind=True, name="app.tasks.processing_tasks.process_file")
def process_file(self, file_ingestion_id: str):
    """
    Process a downloaded file:
    1. Detect format
    2. Run appropriate extractor (CSV, XLSX, PDF, LLM)
    3. Map extracted data to canonical schema
    4. Create EndorsementRecord rows
    5. Dispatch validation task
    """
    raise NotImplementedError("File processing not yet implemented")
