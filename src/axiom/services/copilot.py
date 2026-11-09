"""Copilot service (P12). Runs without ANTHROPIC_API_KEY: status() says so and the UI hides the panel."""

from __future__ import annotations

import functools
import logging
from typing import Any

import anthropic
from sqlalchemy import Engine

from axiom.copilot import agent
from axiom.copilot.tools import Scope
from axiom.services import browse

log = logging.getLogger(__name__)


class CopilotUnavailableError(RuntimeError):
    """No key configured, or the model service failed; the API answers 503."""


def available() -> bool:
    return agent.has_credentials()


def status() -> dict:
    return {"available": available(), "model": agent.model_name()}


@functools.cache
def _client() -> Any:
    return agent.client_from_env()


def query(engine: Engine, project_id: int, question: str) -> agent.Answer:
    if not available():
        raise CopilotUnavailableError("copilot is disabled: ANTHROPIC_API_KEY is not set")
    browse.list_models(engine, project_id)  # LookupError -> 404 for an unknown project
    try:
        return agent.ask(_client(), Scope(engine, project_id), question)
    except anthropic.APIError as e:
        log.exception("copilot model call failed")
        raise CopilotUnavailableError("the model service failed; try again later") from e
