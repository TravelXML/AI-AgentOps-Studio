"""Consistent API error envelope (spec section 46) - never a bare stack trace."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: list[Any] = []
    request_id: str | None = None


class ErrorEnvelope(BaseModel):
    error: ErrorDetail


class ApiError(Exception):
    def __init__(self, status_code: int, code: str, message: str, details: list[Any] | None = None) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or []
        super().__init__(message)
