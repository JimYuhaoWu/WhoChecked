"""
whochecked/jobs.py
------------------
The server's jobs, kept on disk so a reload, a closed tab or a restart loses
nothing (ROADMAP M2, Latency). One file per job, named by a random id:

  queued -> running -> done | failed

The id is the job's link, so it is random and never derived from the query: a
hash of a DOI would let anyone holding that DOI test whether someone asked
about it. A job holds its query and its result and nothing about who sent it.
It is deleted RETENTION after it was submitted, and so is a cached walk
RETENTION after it was fetched: the cache records which papers were asked
about, so it is kept no longer than the jobs that asked.

One worker thread runs the jobs, oldest first, so every OpenAlex request is
spent in one place.
"""

from __future__ import annotations

import json
import os
import re
import secrets
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

RETENTION = timedelta(days=7)

# secrets.token_urlsafe(16): 16 random bytes, 22 characters of base64url.
ID = re.compile(r"[A-Za-z0-9_-]{22}")


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Store:

    def __init__(self, root: Path, cache_dir: Path | None = None):
        self.root = root
        self.cache_dir = cache_dir
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()
        self.wake = threading.Event()

    def _path(self, job_id: str) -> Path | None:
        # The id arrives in a URL, so it is checked before it names a file.
        return self.root / f"{job_id}.json" if ID.fullmatch(job_id) else None

    def _write(self, job_id: str, job: dict) -> None:
        f = self._path(job_id)
        tmp = f.with_suffix(".tmp")
        tmp.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, f)

    def submit(self, query: str, names: list[str]) -> str:
        job_id = secrets.token_urlsafe(16)
        with self.lock:
            self._write(job_id, {"state": "queued", "query": query,
                                 "names": names,
                                 "submitted": _now().isoformat()})
        self.wake.set()
        return job_id

    def get(self, job_id: str) -> dict | None:
        f = self._path(job_id)
        if f is None or not f.exists():
            return None
        return json.loads(f.read_text(encoding="utf-8"))

    def _all(self) -> list[tuple[str, dict]]:
        return [(f.stem, json.loads(f.read_text(encoding="utf-8")))
                for f in self.root.glob("*.json")]

    def next_queued(self) -> str | None:
        with self.lock:
            queued = [(j["submitted"], i) for i, j in self._all()
                      if j["state"] == "queued"]
            if not queued:
                return None
            job_id = min(queued)[1]
            job = self.get(job_id)
            job["state"] = "running"
            self._write(job_id, job)
            return job_id

    def finish(self, job_id: str, *, result: dict | None = None,
               error: str | None = None) -> None:
        with self.lock:
            job = self.get(job_id)
            if job is None:                  # expired while it ran
                return
            job["state"] = "failed" if error else "done"
            job["result"], job["error"] = result, error
            job["finished"] = _now().isoformat()
            self._write(job_id, job)

    def requeue_interrupted(self) -> int:
        """A job left running by a stopped server runs again on start."""
        n = 0
        with self.lock:
            for job_id, job in self._all():
                if job["state"] == "running":
                    job["state"] = "queued"
                    self._write(job_id, job)
                    n += 1
        return n

    def expire(self, now: datetime | None = None) -> int:
        cutoff = (now or _now()) - RETENTION
        n = 0
        with self.lock:
            for job_id, job in self._all():
                if datetime.fromisoformat(job["submitted"]) < cutoff:
                    self._path(job_id).unlink()
                    n += 1
        if self.cache_dir is not None:
            for f in self.cache_dir.glob("*.json"):
                if datetime.fromtimestamp(f.stat().st_mtime, timezone.utc) < cutoff:
                    f.unlink()
                    n += 1
        return n

    def submitted_since(self, since: datetime) -> list[datetime]:
        """When each job still on disk was submitted, if after `since`,
        oldest first."""
        return sorted(t for t in (datetime.fromisoformat(j["submitted"])
                                  for _, j in self._all()) if t > since)

    def position(self, job_id: str) -> int:
        """Jobs queued ahead of this one."""
        job = self.get(job_id)
        return sum(j["state"] == "queued" and j["submitted"] < job["submitted"]
                   for _, j in self._all())


class FailedJob(Exception):
    """A failure whose message is safe to show: it names no query."""


def work(store: Store, run: Callable[[str, list[str]], dict],
         stop: threading.Event, idle: float = 5.0,
         ready: Callable[[], bool] = lambda: True) -> None:
    """
    Run queued jobs until `stop` is set. A FailedJob's message is shown to
    the person who submitted; any other exception is reported only as an
    internal error, because its text may carry anything.

    While `ready()` is false no job starts, and queued jobs wait rather than
    fail: the server passes whether OpenAlex's daily budget can pay for one.
    """
    store.requeue_interrupted()
    while not stop.is_set():
        store.expire()
        job_id = store.next_queued() if ready() else None
        if job_id is None:
            store.wake.wait(idle)
            store.wake.clear()
            continue
        job = store.get(job_id)
        try:
            store.finish(job_id, result=run(job["query"], job["names"]))
        except FailedJob as exc:
            store.finish(job_id, error=str(exc))
        except Exception:                               # noqa: BLE001
            store.finish(job_id, error="internal error")
