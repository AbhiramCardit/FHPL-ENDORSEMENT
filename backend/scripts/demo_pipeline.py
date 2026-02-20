#!/usr/bin/env python3
"""
Demo script — run the pipeline engine locally without Docker/Celery.

Shows single-file and multi-file batch flows, structured logging,
and how insurer-specific steps access per-role extracted data.

Usage:
    cd backend
    python -m scripts.demo_pipeline
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def run_single_file_flow():
    """DEMO 1: Single-file (backward-compat) — like the original."""
    from app.pipeline.engine import PipelineEngine
    from app.pipeline.flow_resolver import FlowResolver

    print("\n" + "=" * 70)
    print("  DEMO 1: Single-File Flow (DEFAULT)")
    print("=" * 70)

    engine = PipelineEngine(flow_resolver=FlowResolver())
    result = await engine.run(
        file_ingestion_id="demo-single-001",
        insuree_id="insuree-default",
        insuree_config={
            "code": "DEFAULT",
            "format_type": "STRUCTURED_CSV",
            "extraction_template": {},
            "min_confidence": 0.80,
            "business_rules": {},
        },
    )
    _print_result(result)


async def run_multi_file_default():
    """DEMO 2: Multi-file batch with DEFAULT flow — no custom API steps."""
    from app.pipeline.engine import PipelineEngine
    from app.pipeline.flow_resolver import FlowResolver

    print("\n" + "=" * 70)
    print("  DEMO 2: Multi-File Batch (DEFAULT flow, 3 files)")
    print("=" * 70)

    engine = PipelineEngine(flow_resolver=FlowResolver())
    result = await engine.run(
        file_ingestion_id="batch-default-001",
        insuree_id="insuree-multi",
        insuree_config={
            "code": "DEFAULT",
            "extraction_template": {},
            "min_confidence": 0.80,
            "business_rules": {},
        },
        files=[
            {"file_id": "f1", "filename": "employees.xlsx", "role": "member_data"},
            {"file_id": "f2", "filename": "endorsement_actions.csv", "role": "endorsement_actions"},
            {"file_id": "f3", "filename": "policy_summary.pdf", "role": "policy_details"},
        ],
    )
    _print_result(result)


async def run_insurer_a_batch():
    """DEMO 3: Insurer A — multi-file with member lookup API after extract."""
    from app.pipeline.engine import PipelineEngine
    from app.pipeline.flow_resolver import FlowResolver

    print("\n" + "=" * 70)
    print("  DEMO 3: Insurer A (multi-file + member lookup API)")
    print("=" * 70)

    engine = PipelineEngine(flow_resolver=FlowResolver())
    result = await engine.run(
        file_ingestion_id="batch-insa-001",
        insuree_id="insuree-a",
        insuree_config={
            "code": "INSURER_A",
            "api_base_url": "https://insurer-a.example.com",
            "extraction_template": {},
            "min_confidence": 0.85,
            "business_rules": {},
        },
        files=[
            {"file_id": "fa1", "filename": "roster.xlsx", "role": "member_data"},
            {"file_id": "fa2", "filename": "changes.csv", "role": "endorsement_actions"},
        ],
    )
    _print_result(result)


async def run_insurer_b_batch():
    """DEMO 4: Insurer B — 3 files + pre/post API calls."""
    from app.pipeline.engine import PipelineEngine
    from app.pipeline.flow_resolver import FlowResolver

    print("\n" + "=" * 70)
    print("  DEMO 4: Insurer B (3 files + policy fetch + endorsement creation APIs)")
    print("=" * 70)

    engine = PipelineEngine(flow_resolver=FlowResolver())
    result = await engine.run(
        file_ingestion_id="batch-insb-001",
        insuree_id="insuree-b",
        insuree_config={
            "code": "INSURER_B",
            "api_base_url": "https://insurer-b.example.com",
            "policy_id": "POL-2026-001",
            "extraction_template": {},
            "min_confidence": 0.75,
            "business_rules": {"max_past_days": 60, "min_age": 1, "max_age": 80},
        },
        files=[
            {"file_id": "fb1", "filename": "endorsements.xlsx", "role": "endorsements"},
            {"file_id": "fb2", "filename": "coverage.pdf", "role": "policy_details"},
            {"file_id": "fb3", "filename": "approval.docx", "role": "approval_letter"},
        ],
    )
    _print_result(result)


def _print_result(result):
    """Pretty-print a PipelineResult."""
    print(f"\n{'─' * 50}")
    print(f"  Execution ID : {result.execution_id[:12]}...")
    print(f"  Status       : {result.status}")
    print(f"  Steps        : {result.steps_completed}/{result.total_steps}")
    print(f"  Duration     : {result.total_duration_ms}ms")
    if result.error:
        print(f"  Error        : {result.error}")

    print(f"\n  Step Results:")
    for sr in result.step_results:
        icon = "✓" if sr["status"] == "COMPLETED" else "✗" if sr["status"] == "FAILED" else "⊘"
        print(f"    {icon} {sr['step_name']} ({sr['duration_ms']}ms)")
        if sr.get("metadata"):
            for k, v in sr["metadata"].items():
                if k == "per_file":
                    print(f"        {k}:")
                    for pf in v:
                        print(f"          - {pf['role']}: {pf['filename']} → {pf.get('records', '?')} records ({pf['status']})")
                elif k == "by_role":
                    print(f"        {k}: {v}")
                elif k == "detections":
                    print(f"        {k}:")
                    for d in v:
                        print(f"          - {d['role']}: {d['format']} (via {d['source']})")
                elif k == "files":
                    print(f"        {k}:")
                    for f in v:
                        ok = "✓" if f["ok"] else "✗"
                        print(f"          {ok} {f['role']}: {f['filename']}")
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
            print(f"    ⚠  Errors: {cs['errors']}")

    print(f"{'─' * 50}\n")


async def main():
    from app.core.logging import setup_logging
    setup_logging("WARNING")     # quiet logs, show formatted output only

    print("\n╔" + "═" * 68 + "╗")
    print("║      FHPL ENDORSEMENT — PIPELINE ENGINE DEMO (Multi-File)       ║")
    print("╚" + "═" * 68 + "╝")

    await run_single_file_flow()
    await run_multi_file_default()
    await run_insurer_a_batch()
    await run_insurer_b_batch()

    print("\n✅ All demos completed successfully!")
    print("   Demos 2-4 show multi-file batch processing with per-role extraction.\n")


if __name__ == "__main__":
    asyncio.run(main())
