"""
Celery application configuration.
"""

# Broker
broker_url = "redis://localhost:6379/0"
result_backend = "redis://localhost:6379/1"

# Serialization
accept_content = ["json"]
task_serializer = "json"
result_serializer = "json"

# Timezone
timezone = "UTC"
enable_utc = True

# Task routing
task_routes = {
    "app.tasks.ingestion_tasks.*": {"queue": "ingestion"},
    "app.tasks.processing_tasks.*": {"queue": "processing"},
    "app.tasks.validation_tasks.*": {"queue": "validation"},
    "app.tasks.submission_tasks.*": {"queue": "submission"},
}

# Retry defaults
task_acks_late = True
task_reject_on_worker_lost = True
worker_prefetch_multiplier = 1
