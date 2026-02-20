"""
SFTP Poller — connects to insuree SFTP servers and downloads new files.
"""

from typing import Any


def poll_sftp_for_insuree(insuree_id: str) -> list[dict[str, Any]]:
    """
    Poll SFTP server for a specific insuree and download new files.

    Steps:
    1. Load insuree SFTP config from DB
    2. Open SFTP connection using Paramiko
    3. List files in watch folder
    4. Filter by allowed extensions
    5. Check MD5 hash against processed_files
    6. Download new files to local staging
    7. Upload to S3/MinIO
    8. Move files to /processing/ on SFTP
    9. Return list of downloaded file records
    """
    raise NotImplementedError("SFTP polling not yet implemented")


def open_sftp_connection(config: dict) -> Any:
    """Open SFTP connection using Paramiko."""
    raise NotImplementedError
