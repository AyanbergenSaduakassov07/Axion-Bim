from dataclasses import replace

import pytest

from axiom.config import Settings
from axiom.jobs import Runner
from axiom.repo.db import get_engine, migrate
from axiom.services import jobs
from tests.jobkinds import TEST_KINDS


@pytest.fixture
def env(tmp_path):
    settings = Settings(data_dir=tmp_path, db_url=f"sqlite:///{tmp_path / 'a.db'}", job_timeout_s=5)
    engine = get_engine(settings.db_url)
    migrate(engine)
    return engine, settings


def _run(engine, settings, kind, payload):
    job_id = jobs.enqueue(engine, kind, payload, kinds=TEST_KINDS)
    Runner(engine, settings, TEST_KINDS).run_once()
    return jobs.get_job(engine, job_id)


def test_job_runs_in_child_and_stores_result(env):
    job = _run(*env, "echo", {"x": 7})
    assert job["status"] == "done" and job["result"] == {"echo": 7} and job["progress"] == 1.0


def test_timeout_ends_in_error(env):
    engine, settings = env
    job = _run(engine, replace(settings, job_timeout_s=0.5), "sleep", {"s": 30})
    assert job["status"] == "error" and "time limit" in job["error_message"]


def test_native_crash_ends_in_error_and_runner_survives(env):
    job = _run(*env, "abort", {})
    assert job["status"] == "error" and "crashed" in job["error_message"]
    assert _run(*env, "echo", {"x": 1})["status"] == "done"


def test_exception_message_is_not_leaked(env):
    job = _run(*env, "boom", {})
    assert job["status"] == "error" and "/secret" not in job["error_message"]


def test_unknown_kind_is_rejected_at_enqueue(env):
    with pytest.raises(ValueError, match="unknown job kind"):
        jobs.enqueue(env[0], "rm -rf", {}, kinds=TEST_KINDS)


def test_orphaned_running_jobs_fail_on_start(env):
    engine, settings = env
    job_id = jobs.enqueue(engine, "echo", {"x": 1}, kinds=TEST_KINDS)
    assert jobs.claim_next(engine).id == job_id
    Runner(engine, settings, TEST_KINDS).recover()
    job = jobs.get_job(engine, job_id)
    assert job["status"] == "error" and "restarted" in job["error_message"]
