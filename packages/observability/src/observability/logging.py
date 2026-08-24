"""Structured logging. Every log line carries request/workspace/project/flow/run/node ids
when available (section 47), and is JSON in production so log aggregators can index it."""

from __future__ import annotations

import logging
import sys

import structlog

_configured = False


def configure_logging(*, json: bool = True, level: int = logging.INFO) -> None:
    global _configured
    if _configured:
        return

    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    renderer = structlog.processors.JSONRenderer() if json else structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[*shared_processors, structlog.processors.format_exc_info, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )
    _configured = True


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)


def bind_context(**kwargs: object) -> None:
    """Bind request-scoped fields (request_id, workspace_id, flow_id, run_id, node_id, ...)."""
    structlog.contextvars.bind_contextvars(**kwargs)


def clear_context() -> None:
    structlog.contextvars.clear_contextvars()
