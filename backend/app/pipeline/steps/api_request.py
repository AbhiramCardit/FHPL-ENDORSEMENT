"""
APIRequestStep — configurable step for making intermediate API calls.

This is the key building block for insurer-specific flows.  Each instance
is configured with a URL, method, request builder, and response key.
The response is stored in ctx.api_responses[response_key] for downstream steps.

Usage in FlowResolver::

    APIRequestStep(
        step_name="fetch_policy",
        step_description="Fetch policy details from insurer API",
        method="GET",
        url_template="{base_url}/api/policies/{policy_id}",
        response_key="policy_details",
        retryable=True,
    )
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

import httpx

from app.core.constants import APIRequestMethod
from app.core.logging import get_logger
from app.pipeline.context import PipelineContext, StepResult
from app.pipeline.errors import APIRequestError, StepExecutionError
from app.pipeline.step import PipelineStep

logger = get_logger(__name__)

# Default timeout for API calls (seconds)
DEFAULT_TIMEOUT = 30


class APIRequestStep(PipelineStep):
    """
    Configurable step for making HTTP API calls during the pipeline.

    Supports GET, POST, PUT, PATCH, DELETE.
    Request body is built dynamically from the pipeline context.
    Response is stored in ctx.api_responses for downstream steps.
    """

    def __init__(
        self,
        step_name: str,
        step_description: str,
        method: str = "GET",
        url_template: str = "",
        headers_builder: Callable[[PipelineContext], dict[str, str]] | None = None,
        request_builder: Callable[[PipelineContext], dict[str, Any]] | None = None,
        response_key: str = "api_response",
        timeout: int = DEFAULT_TIMEOUT,
        retryable: bool = True,
        max_retries: int = 3,
        expected_status_codes: list[int] | None = None,
    ) -> None:
        """
        Args:
            step_name: Unique identifier for this step instance.
            step_description: Human-readable description for logs/UI.
            method: HTTP method (GET, POST, etc.).
            url_template: URL with optional {placeholders} resolved from ctx.
            headers_builder: Optional callable to build request headers from ctx.
            request_builder: Optional callable to build request body from ctx.
            response_key: Key to store response in ctx.api_responses.
            timeout: HTTP timeout in seconds.
            retryable: Whether to retry on failure.
            max_retries: Max retry attempts.
            expected_status_codes: Acceptable status codes (default: [200, 201, 202]).
        """
        self.name = step_name
        self.description = step_description
        self._method = method.upper()
        self._url_template = url_template
        self._headers_builder = headers_builder
        self._request_builder = request_builder
        self._response_key = response_key
        self._timeout = timeout
        self.retryable = retryable
        self.max_retries = max_retries
        self._expected_status = expected_status_codes or [200, 201, 202]

    async def execute(self, ctx: PipelineContext) -> StepResult:
        started_at = self._now()

        try:
            # ── Build URL ─────────────────────────────
            url = self._resolve_url(ctx)

            # ── Build headers ─────────────────────────
            headers = {"Content-Type": "application/json"}
            if self._headers_builder:
                headers.update(self._headers_builder(ctx))

            # ── Build request body ────────────────────
            body = None
            if self._request_builder:
                body = self._request_builder(ctx)

            logger.info(
                "Making API request",
                step=self.name,
                method=self._method,
                url=url,
                has_body=body is not None,
            )

            # ── Execute HTTP request ──────────────────
            # TODO: Replace with real httpx call when ready
            # For now, simulate the API call with a placeholder response.
            #
            # Real implementation:
            #   async with httpx.AsyncClient(timeout=self._timeout) as client:
            #       if self._method == "GET":
            #           response = await client.get(url, headers=headers)
            #       elif self._method == "POST":
            #           response = await client.post(url, headers=headers, json=body)
            #       elif self._method == "PUT":
            #           response = await client.put(url, headers=headers, json=body)
            #       elif self._method == "PATCH":
            #           response = await client.patch(url, headers=headers, json=body)
            #       elif self._method == "DELETE":
            #           response = await client.delete(url, headers=headers)
            #
            #       if response.status_code not in self._expected_status:
            #           raise APIRequestError(
            #               f"API returned {response.status_code}",
            #               status_code=response.status_code,
            #               response_body=response.text,
            #           )
            #
            #       response_data = response.json()

            # Placeholder response
            response_data = {
                "status": "success",
                "message": f"Placeholder response for {self.name}",
                "method": self._method,
                "url": url,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            # ── Store response in context ─────────────
            ctx.api_responses[self._response_key] = response_data
            ctx.set_extra(self._response_key, response_data)

            logger.info(
                "API request successful",
                step=self.name,
                response_key=self._response_key,
            )

            return self._success(started_at, metadata={
                "method": self._method,
                "url": url,
                "response_key": self._response_key,
                "status": "placeholder",
            })

        except APIRequestError:
            raise
        except Exception as exc:
            raise StepExecutionError(
                f"API request failed: {exc}",
                execution_id=ctx.execution_id,
                step_name=self.name,
            ) from exc

    def _resolve_url(self, ctx: PipelineContext) -> str:
        """
        Resolve {placeholders} in the URL template from context.

        Supported placeholders:
            {base_url}   — from insuree_config or settings
            {insuree_id} — from ctx
            {policy_id}  — from ctx.extra
            ...any key from ctx.extra or ctx.insuree_config
        """
        url = self._url_template

        # Standard replacements
        replacements = {
            "base_url": ctx.insuree_config.get("api_base_url", "https://api.example.com"),
            "insuree_id": ctx.insuree_id,
            "file_id": ctx.file_ingestion_id,
            "execution_id": ctx.execution_id,
        }

        # Add all extra context values
        for key, value in ctx.extra.items():
            if isinstance(value, str):
                replacements[key] = value
            elif isinstance(value, dict) and "id" in value:
                replacements[f"{key}_id"] = str(value["id"])

        # Add insuree config values
        for key, value in ctx.insuree_config.items():
            if isinstance(value, str):
                replacements[key] = value

        try:
            url = url.format(**replacements)
        except KeyError as exc:
            logger.warning(
                "URL placeholder not resolved",
                url_template=self._url_template,
                missing_key=str(exc),
            )

        return url
