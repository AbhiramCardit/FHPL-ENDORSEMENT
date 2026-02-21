"""
Celery configuration — best practices for the endorsements pipeline.

Loaded by `celery_app.config_from_object("celeryconfig")` in app/tasks/__init__.py.
All broker/result-backend URLs come from environment variables,
defaulting to localhost for local dev.
"""

import os

# ═══════════════════════════════════════════════════════════
#  Broker & Result Backend
# ═══════════════════════════════════════════════════════════

broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

# ═══════════════════════════════════════════════════════════
#  Serialization — JSON only (no pickle = no arbitrary code exec)
# ═══════════════════════════════════════════════════════════

task_serializer = "json"
result_serializer = "json"
accept_content = ["json"]

# ═══════════════════════════════════════════════════════════
#  Timezone
# ═══════════════════════════════════════════════════════════

timezone = "UTC"
enable_utc = True

# ═══════════════════════════════════════════════════════════
#  Task Execution
# ═══════════════════════════════════════════════════════════

# Acknowledge tasks AFTER they complete (crash-safe: prevents lost tasks)
task_acks_late = True
task_reject_on_worker_lost = True

# Only prefetch 1 task at a time per worker process
# Prevents one slow pipeline from blocking other tasks
worker_prefetch_multiplier = 1

# Pipeline tasks can take a while (LLM calls, large files)
task_soft_time_limit = 1800   # 30 min: raises SoftTimeLimitExceeded
task_time_limit = 1860        # 31 min: hard kill

# ═══════════════════════════════════════════════════════════
#  Retry Policy
# ═══════════════════════════════════════════════════════════

task_default_retry_delay = 60         # 1 minute between retries
task_max_retries = 3

# ═══════════════════════════════════════════════════════════
#  Result Expiry — auto-clean after 24h
# ═══════════════════════════════════════════════════════════

result_expires = 86400

# ═══════════════════════════════════════════════════════════
#  Worker Settings
# ═══════════════════════════════════════════════════════════

# Restart worker after N tasks (prevents memory leaks from LLM libraries)
worker_max_tasks_per_child = 50

# Disable events by default (reduces Redis load)
# Enable with: celery -A app.tasks worker -E
worker_send_task_events = False
task_send_sent_event = False

# ═══════════════════════════════════════════════════════════
#  Task Routes — separate queues for workload isolation
# ═══════════════════════════════════════════════════════════
# Run dedicated workers per queue:
#   celery -A app.tasks worker -Q pipeline      (heavy: LLM + extraction)
#   celery -A app.tasks worker -Q submissions    (API calls to TPA)
#   celery -A app.tasks worker -Q default        (light: ingestion, validation)

task_routes = {
    "app.tasks.processing_tasks.*": {"queue": "pipeline"},
    "app.tasks.submission_tasks.*": {"queue": "submissions"},
    "app.tasks.ingestion_tasks.*": {"queue": "default"},
    "app.tasks.validation_tasks.*": {"queue": "default"},
}

task_default_queue = "default"

# ═══════════════════════════════════════════════════════════
#  Beat Schedule (periodic tasks)
# ═══════════════════════════════════════════════════════════
# Example:
#   beat_schedule = {
#       "check-stale-submissions": {
#           "task": "app.tasks.submission_tasks.check_stale",
#           "schedule": 300.0,
#       },
#   }
beat_schedule = {}
