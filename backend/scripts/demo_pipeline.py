#!/usr/bin/env python3
"""
Demo script — test the ABHI (Aditya Birla Health Insurance) pipeline.

Usage:
    cd backend
    python -m scripts.demo_pipeline
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def run_abhi_pipeline():
    """ABHI pipeline: XLS endorsement sheet + PDF via Gemini LLM."""
    from app.pipeline.engine import PipelineEngine
    from app.pipeline.flow_resolver import FlowResolver
    from app.pipeline.insurers.abhi import ABHI_CONFIG

    XLS_PATH = r"C:\Users\abhir\Downloads\Insurers\Insurers\ABHI\2-81-25-0004690-000-AE-002_Annexure.xls_1765288875336.xls"
    PDF_PATH = r"C:\Users\abhir\Downloads\Insurers\Insurers\ABHI\2-81-25-0004690-000-AE-002_Schedule.pdf_1765288875306.pdf"

    engine = PipelineEngine(flow_resolver=FlowResolver())
    result = await engine.run(
        file_ingestion_id="abhi-batch-001",
        insuree_id="abhi-insuree-001",
        insuree_config=ABHI_CONFIG,
        files=[
            {"file_id": "abhi-f1", "filename": "Annexure.xls", "role": "endorsement_data", "s3_key": XLS_PATH},
            {"file_id": "abhi-f2", "filename": "Schedule.pdf", "role": "endorsement_pdf", "s3_key": PDF_PATH},
        ],
    )
    return result


def _print_result(result):
    """Pretty-print a PipelineResult."""
    print(f"\n{'─' * 60}")
    print(f"  Execution ID : {result.execution_id}")
    print(f"  Status       : {result.status}")
    print(f"  Steps        : {result.steps_completed}/{result.total_steps}")
    print(f"  Duration     : {result.total_duration_ms}ms")
    if result.error:
        print(f"  Error        : {result.error}")

    print(f"\n  Step Results:")
    for sr in result.step_results:
        icon = "+" if sr["status"] == "COMPLETED" else "X" if sr["status"] == "FAILED" else "-"
        print(f"    [{icon}] {sr['step_name']} ({sr['duration_ms']}ms)")
        if sr.get("metadata"):
            for k, v in sr["metadata"].items():
                if k == "per_file":
                    print(f"        {k}:")
                    for pf in v:
                        print(f"          - {pf.get('role','?')}: {pf.get('filename','?')} -> {pf.get('records', '?')} records ({pf['status']})")
                elif k == "by_role":
                    print(f"        {k}: {v}")
                elif k == "detections":
                    print(f"        {k}:")
                    for d in v:
                        print(f"          - {d['role']}: {d['format']} (via {d['source']})")
                elif k == "files":
                    print(f"        {k}:")
                    for f in v:
                        ok = "OK" if f["ok"] else "FAIL"
                        print(f"          [{ok}] {f['role']}: {f['filename']}")
                else:
                    print(f"        {k}: {v}")

    cs = result.context_summary
    if cs:
        print(f"\n  Context Summary:")
        print(f"    Total files  : {cs.get('total_files', 1)}")
        print(f"    Is batch     : {cs.get('is_batch', False)}")
        if cs.get("extracted_by_role"):
            print(f"    Extracted by role:")
            for role, count in cs["extracted_by_role"].items():
                print(f"      - {role}: {count} records")
        print(f"    Total records: {cs.get('records_extracted_total', 0)}")
        print(f"    Canonical    : {cs.get('records_canonical', 0)}")
        print(f"    For submit   : {cs.get('records_for_submission', 0)}")
        print(f"    For review   : {cs.get('records_for_review', 0)}")
        if cs.get("errors"):
            print(f"    Errors:")
            for e in cs["errors"]:
                print(f"      - {e}")

    print(f"{'─' * 60}\n")


async def main():
    from app.core.logging import setup_logging
    from app.core.tracing import setup_tracing
    setup_logging("WARNING")
    setup_tracing()

    print("\n" + "=" * 60)
    print("  ABHI Pipeline Test (Aditya Birla Health Insurance)")
    print("  Files: endorsement_data.xls + endorsement_letter.pdf")
    print("=" * 60)

    result = await run_abhi_pipeline()
    _print_result(result)

    if result.status == "COMPLETED":
        print("  PASSED - ABHI pipeline completed successfully!\n")
    else:
        print(f"  FAILED - {result.error}\n")


if __name__ == "__main__":
    asyncio.run(main())
