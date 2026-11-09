"""FastAPI app factory. Routes call services only; IFC work runs in the job runner (D-06, D-18)."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from axiom import __version__
from axiom.api.routes import router
from axiom.config import Settings, load_settings
from axiom.jobs import Runner
from axiom.repo.db import get_engine, migrate
from axiom.services import jobs
from axiom.services.copilot import CopilotUnavailableError
from axiom.services.uploads import TooLargeError

log = logging.getLogger(__name__)


def create_app(
    settings: Settings | None = None,
    *,
    kinds: dict[str, str] = jobs.KINDS,
    poll_s: float = 1.0,
    run_jobs: bool = True,
) -> FastAPI:
    settings = settings or load_settings()
    engine = get_engine(settings.db_url)
    runner = Runner(engine, settings, kinds)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        migrate(engine)
        if run_jobs:
            runner.start(poll_s)
        yield
        runner.stop()

    app = FastAPI(title="Axiom BIM", version=__version__, lifespan=lifespan)
    app.state.engine, app.state.settings, app.state.kinds = engine, settings, kinds

    def enqueue(kind: str, payload: dict) -> int:
        job_id = jobs.enqueue(engine, kind, payload, kinds=kinds)
        runner.wake()
        return job_id

    app.state.enqueue, app.state.wake = enqueue, runner.wake
    _install_error_handlers(app)
    app.include_router(router, prefix="/api/v1")
    return app


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse({"error": {"code": code, "message": message}}, status_code=status)


def _install_error_handlers(app: FastAPI) -> None:
    """Every error is {error: {code, message}}; messages never carry paths or tracebacks."""

    @app.exception_handler(LookupError)
    async def not_found(_: Request, e: LookupError) -> JSONResponse:
        return _error(404, "not_found", str(e.args[0]) if e.args else "not found")

    @app.exception_handler(TooLargeError)
    async def too_large(_: Request, e: TooLargeError) -> JSONResponse:
        return _error(413, "payload_too_large", str(e))

    @app.exception_handler(CopilotUnavailableError)
    async def copilot_unavailable(_: Request, e: CopilotUnavailableError) -> JSONResponse:
        return _error(503, "copilot_unavailable", str(e))

    @app.exception_handler(ValueError)
    async def invalid(_: Request, e: ValueError) -> JSONResponse:
        return _error(400, "invalid_request", str(e))

    @app.exception_handler(RequestValidationError)
    async def validation(_: Request, e: RequestValidationError) -> JSONResponse:
        fields = ", ".join(".".join(str(p) for p in err["loc"]) for err in e.errors())
        return _error(422, "validation_error", f"invalid or missing: {fields}")

    @app.exception_handler(HTTPException)
    async def http(_: Request, e: HTTPException) -> JSONResponse:
        return _error(e.status_code, f"http_{e.status_code}", str(e.detail))

    @app.exception_handler(Exception)
    async def internal(_: Request, e: Exception) -> JSONResponse:
        log.exception("unhandled error", exc_info=e)
        return _error(500, "internal_error", "internal error; see the server log")
