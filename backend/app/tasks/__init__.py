"""
Celery application factory.
"""

from celery import Celery

celery_app = Celery("endorsements")
celery_app.config_from_object("celeryconfig")

# Auto-discover tasks in these modules
celery_app.autodiscover_tasks([
    "app.tasks.ingestion_tasks",
    "app.tasks.processing_tasks",
    "app.tasks.validation_tasks",
    "app.tasks.submission_tasks",
])
