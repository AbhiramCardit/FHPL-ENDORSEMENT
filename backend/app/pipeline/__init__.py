"""
Pipeline Engine — enterprise-grade document processing orchestrator.

This package provides the step-based pipeline engine that processes
endorsement files through a configurable sequence of steps, with
per-step logging, error handling, and audit tracking.
"""

from app.pipeline.engine import PipelineEngine
from app.pipeline.context import PipelineContext, FileInfo, StepResult
from app.pipeline.step import PipelineStep

__all__ = ["PipelineEngine", "PipelineContext", "PipelineStep", "FileInfo", "StepResult"]

