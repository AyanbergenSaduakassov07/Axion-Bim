"""Copilot service (P12). Runs without ANTHROPIC_API_KEY: status() says so and the UI hides the panel."""

from __future__ import annotations

import functools
import logging
import threading
import time
from collections import deque
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

import anthropic
from sqlalchemy import Engine

from axiom.copilot import agent
from axiom.copilot.tools import Scope
from axiom.services import browse

log = logging.getLogger(__name__)


class CopilotUnavailableError(RuntimeError):
    """No key configured, or the model service failed; the API answers 503."""


class CopilotBusyError(RuntimeError):
    """A query is already running, or the per-minute budget is spent; the API answers 429."""


class Limiter:
    """One query in flight and at most `per_window` started per `window_s` (each query is a multi-call
    tool loop, so this caps model spend and a runaway client). Process-local: one API worker (D-26)."""

    def __init__(self, per_window: int, window_s: float, clock: Callable[[], float] = time.monotonic):
        self._per_window, self._window_s, self._clock = per_window, window_s, clock
        self._started: deque[float] = deque()
        self._lock = threading.Lock()
        self._running = False

    @contextmanager
    def slot(self) -> Iterator[None]:
        with self._lock:
            now = self._clock()
            while self._started and now - self._started[0] >= self._window_s:
                self._started.popleft()
            if self._running:
                raise CopilotBusyError("another copilot question is still being answered")
            if len(self._started) >= self._per_window:
                raise CopilotBusyError(
                    f"copilot limit is {self._per_window} questions per minute; wait a moment"
                )
            self._started.append(now)
            self._running = True
        try:
            yield
        finally:
            with self._lock:
                self._running = False


LIMIT = Limiter(per_window=10, window_s=60.0)


def available() -> bool:
    return agent.has_credentials()


def status() -> dict:
    return {"available": available(), "model": agent.model_name()}


@functools.cache
def _client() -> Any:
    return agent.client_from_env()


def query(
    engine: Engine, project_id: int, question: str, history: list[tuple[str, str]] | None = None
) -> agent.Answer:
    if not available():
        raise CopilotUnavailableError("copilot is disabled: ANTHROPIC_API_KEY is not set")
    browse.list_models(engine, project_id)  # LookupError -> 404 for an unknown project
    try:
        with LIMIT.slot():
            return agent.ask(_client(), Scope(engine, project_id), question, history=history or ())
    except anthropic.APIError as e:
        log.exception("copilot model call failed")
        raise CopilotUnavailableError("the model service failed; try again later") from e
