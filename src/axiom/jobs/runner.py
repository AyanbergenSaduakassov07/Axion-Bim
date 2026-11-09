"""One background thread; each job runs in a spawned child with memory + wall-clock limits (D-06, D-18).

A child crash (segfault in native IFC code), timeout or exception ends the job in `error` with a
user-safe message; the API process is never affected.
"""

from __future__ import annotations

import importlib
import logging
import multiprocessing as mp
import resource
import threading
from multiprocessing.connection import Connection

from sqlalchemy import Engine

from axiom.config import Settings
from axiom.services import jobs

log = logging.getLogger(__name__)
GENERIC_ERROR = "processing failed; see the server log for details"


class Runner:
    def __init__(self, engine: Engine, settings: Settings, kinds: dict[str, str] = jobs.KINDS) -> None:
        self.engine, self.settings, self.kinds = engine, settings, kinds
        self._wake, self._stop = threading.Event(), threading.Event()
        self._thread: threading.Thread | None = None

    def recover(self) -> int:
        """Jobs left `running` by a dead process can never finish: mark them failed."""
        n = jobs.fail_orphans(self.engine)
        if n:
            log.warning("marked %d orphaned running job(s) as error", n)
        return n

    def run_once(self) -> bool:
        job = jobs.claim_next(self.engine)
        if job is None:
            return False
        result, error = _execute(self.kinds[job.kind], job.payload_json, self.settings)
        if error:
            log.error("job %s (%s) failed: %s", job.id, job.kind, error)
        jobs.finish(self.engine, job.id, result=result, error=error)
        return True

    def start(self, poll_s: float = 1.0) -> None:
        self.recover()
        self._thread = threading.Thread(target=self._loop, args=(poll_s,), name="axiom-jobs", daemon=True)
        self._thread.start()

    def wake(self) -> None:
        self._wake.set()

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()
        if self._thread is not None:
            self._thread.join(timeout=self.settings.job_timeout_s + 5)

    def _loop(self, poll_s: float) -> None:
        while not self._stop.is_set():
            try:
                if self.run_once():
                    continue
            except Exception:  # a DB hiccup must not kill the runner thread
                log.exception("job runner iteration failed")
            self._wake.wait(poll_s)
            self._wake.clear()


def _execute(target: str, payload: dict, settings: Settings) -> tuple[dict | None, str | None]:
    ctx = mp.get_context("spawn")  # fork is unsafe with threads and native libraries
    recv, send = ctx.Pipe(duplex=False)
    proc = ctx.Process(target=_child, args=(target, payload, settings, send), daemon=True)
    proc.start()
    send.close()
    try:
        # poll() also returns on EOF, so a crashed child is noticed at once, not at the timeout
        if not recv.poll(settings.job_timeout_s):
            proc.kill()
            return None, f"exceeded the time limit of {settings.job_timeout_s:g} s"
        try:
            status, value = recv.recv()
        except EOFError:
            proc.join(5)
            log.error("job child exited with code %s", proc.exitcode)
            return None, "the processing worker crashed (the file may be malformed or too large)"
        return (value, None) if status == "ok" else (None, value)
    finally:
        proc.join(5)
        if proc.is_alive():
            proc.kill()
        recv.close()


def _child(target: str, payload: dict, settings: Settings, conn: Connection) -> None:
    logging.basicConfig(level=logging.INFO)
    _limit_memory(settings.job_mem_mb)
    try:
        module, func = target.split(":")
        result = getattr(importlib.import_module(module), func)(payload, settings)
        conn.send(("ok", result))
    except ValueError as e:  # our services raise ValueError with user-facing messages
        log.warning("job rejected: %s", e)
        conn.send(("error", str(e)))
    except MemoryError:
        conn.send(("error", "exceeded the memory limit"))
    except Exception:
        log.exception("job failed")
        conn.send(("error", GENERIC_ERROR))
    finally:
        conn.close()


def _limit_memory(mb: int) -> None:
    try:
        limit = mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
    except (ValueError, OSError) as e:  # macOS does not support RLIMIT_AS; the timeout still applies
        log.debug("memory limit not applied: %s", e)
