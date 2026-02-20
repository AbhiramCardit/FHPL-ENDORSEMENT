"""
Processing Pipeline — orchestrates the full extraction flow.
"""


def process_file(file_ingestion_id: str) -> None:
    """
    Full processing pipeline:
    1. Load file from S3
    2. Detect format
    3. Run extractor
    4. Map to canonical schema
    5. Create EndorsementRecord rows
    6. Dispatch validation
    """
    raise NotImplementedError("Processing pipeline not yet implemented")
