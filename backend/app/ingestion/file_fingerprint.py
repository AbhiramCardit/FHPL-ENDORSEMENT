"""
File fingerprinting — MD5/SHA hash for deduplication.
"""

import hashlib


def compute_file_hash(filepath: str, algorithm: str = "md5") -> str:
    """Compute hash of a local file for deduplication."""
    h = hashlib.new(algorithm)
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def is_already_processed(file_hash: str) -> bool:
    """Check if this file hash already exists in the DB."""
    raise NotImplementedError("DB lookup not yet implemented")
