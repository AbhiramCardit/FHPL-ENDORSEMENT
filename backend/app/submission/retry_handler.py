"""Exponential backoff retry logic for TPA submissions."""


def should_retry(status_code: int, attempt: int, max_retries: int = 5) -> bool:
    """Determine if a failed submission should be retried."""
    if attempt >= max_retries:
        return False
    return status_code >= 500  # Only retry server errors
