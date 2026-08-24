from __future__ import annotations

import uuid
from contextlib import AsyncExitStack, asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from agentq_api.config import get_settings
from agentq_api.routers import (
    architect,
    evaluations,
    flows,
    health,
    knowledge,
    mcp_servers,
    model_configs,
    runs,
    tools,
)
from agentq_api.routers import (
    settings as settings_router,
)
from agentq_api.schemas.errors import ApiError, ErrorDetail, ErrorEnvelope
from agentq_runtime.checkpointer import memory_checkpointer, postgres_checkpointer
from observability import configure_logging, get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(json=settings.app_env != "development")

    if settings.app_secret == "dev-insecure-secret-change-me" and settings.app_env != "development":
        logger.warning(
            "agentq_api.insecure_default_secret",
            message="APP_SECRET is still the insecure default - set a real secret before deploying.",
        )

    async with AsyncExitStack() as stack:
        if settings.use_postgres_checkpointer:
            checkpointer = await stack.enter_async_context(
                postgres_checkpointer(settings.checkpointer_database_url)
            )
        else:
            checkpointer = memory_checkpointer()
        app.state.checkpointer = checkpointer
        logger.info("agentq_api.startup", env=settings.app_env)
        yield
    logger.info("agentq_api.shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="AgentQ API",
        description=(
            "Enterprise Agent Engineering Platform - build, test, secure, deploy, "
            "observe, and optimize AI agents."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        # Custom response headers (X-Run-Id) are invisible to client-side JS on a cross-origin
        # fetch unless explicitly exposed - the frontend reads this header to open the trace
        # page and to resume/replay the exact run it just started.
        expose_headers=["X-Run-Id", "X-Total-Count"],
    )

    @app.exception_handler(ApiError)
    async def handle_api_error(request: Request, exc: ApiError) -> JSONResponse:
        request_id = str(uuid.uuid4())
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorEnvelope(
                error=ErrorDetail(
                    code=exc.code, message=exc.message, details=exc.details, request_id=request_id
                )
            ).model_dump(mode="json"),
        )

    @app.exception_handler(ValidationError)
    async def handle_validation_error(request: Request, exc: ValidationError) -> JSONResponse:
        request_id = str(uuid.uuid4())
        return JSONResponse(
            status_code=422,
            content=ErrorEnvelope(
                error=ErrorDetail(
                    code="VALIDATION_ERROR",
                    message="Request failed validation.",
                    details=exc.errors(include_url=False),
                    request_id=request_id,
                )
            ).model_dump(mode="json"),
        )

    app.include_router(health.router)
    app.include_router(flows.router)
    app.include_router(runs.router)
    app.include_router(model_configs.router)
    app.include_router(tools.router)
    app.include_router(architect.router)
    app.include_router(knowledge.router)
    app.include_router(mcp_servers.router)
    app.include_router(evaluations.router)
    app.include_router(settings_router.router)

    return app


app = create_app()
