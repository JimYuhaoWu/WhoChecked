"""
tests/test_jobs.py
------------------
The on-disk job store and its worker, offline, on invented queries.

    python -m unittest discover tests
"""

import os
import tempfile
import threading
import time
import unittest
from datetime import timedelta
from pathlib import Path

from whochecked import jobs


class Store(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = jobs.Store(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_id_is_random_and_not_the_query(self):
        a = self.store.submit("10.0000/example.1", [])
        b = self.store.submit("10.0000/example.1", [])
        self.assertNotEqual(a, b)
        self.assertRegex(a, jobs.ID)
        self.assertNotIn("example", a)

    def test_job_holds_nothing_but_query_and_state(self):
        j = self.store.get(self.store.submit("10.0000/example.1", ["Widgetron"]))
        self.assertEqual(set(j), {"state", "query", "names", "submitted"})

    def test_ids_that_could_name_another_file_are_refused(self):
        for bad in ("../../etc/passwd", "a" * 21, "a" * 23, "x.json", ""):
            self.assertIsNone(self.store.get(bad))

    def test_lifecycle(self):
        i = self.store.submit("q", [])
        self.assertEqual(self.store.next_queued(), i)
        self.assertEqual(self.store.get(i)["state"], "running")
        self.store.finish(i, result={"ok": 1})
        self.assertEqual((self.store.get(i)["state"], self.store.get(i)["result"]),
                         ("done", {"ok": 1}))
        self.assertIsNone(self.store.next_queued())

    def test_oldest_first_and_position(self):
        a, b = self.store.submit("a", []), self.store.submit("b", [])
        self.assertEqual((self.store.position(a), self.store.position(b)), (0, 1))
        self.assertEqual(self.store.next_queued(), a)

    def test_a_job_left_running_survives_a_restart(self):
        i = self.store.submit("q", [])
        self.store.next_queued()
        again = jobs.Store(Path(self.tmp.name))
        self.assertEqual(again.requeue_interrupted(), 1)
        self.assertEqual(again.next_queued(), i)

    def test_expiry(self):
        i = self.store.submit("q", [])
        self.assertEqual(self.store.expire(), 0)
        later = jobs._now() + jobs.RETENTION + timedelta(seconds=1)
        self.assertEqual(self.store.expire(later), 1)
        self.assertIsNone(self.store.get(i))

    def test_the_cache_expires_with_the_jobs(self):
        cache = Path(self.tmp.name) / "cache"
        cache.mkdir()
        old, new = cache / "citing_W1.json", cache / "citing_W2.json"
        old.write_text("{}"), new.write_text("{}")
        aged = time.time() - jobs.RETENTION.total_seconds() - 60
        os.utime(old, (aged, aged))
        store = jobs.Store(Path(self.tmp.name) / "jobs", cache_dir=cache)
        self.assertEqual(store.expire(), 1)
        self.assertEqual((old.exists(), new.exists()), (False, True))

    def test_submitted_since(self):
        self.store.submit("a", []), self.store.submit("b", [])
        hour_ago = jobs._now() - timedelta(hours=1)
        self.assertEqual(len(self.store.submitted_since(hour_ago)), 2)
        self.assertEqual(self.store.submitted_since(jobs._now()), [])


class Worker(unittest.TestCase):

    def run_one(self, run):
        with tempfile.TemporaryDirectory() as d:
            store = jobs.Store(Path(d))
            i = store.submit("q", ["N"])
            stop = threading.Event()

            def once(query, names):
                stop.set()
                return run(query, names)
            jobs.work(store, once, stop, idle=0)
            return store.get(i)

    def test_result_is_stored(self):
        j = self.run_one(lambda q, n: {"q": q, "n": n})
        self.assertEqual((j["state"], j["result"]), ("done", {"q": "q", "n": ["N"]}))

    def test_a_safe_failure_is_shown(self):
        def fail(q, n):
            raise jobs.FailedJob("OpenAlex did not answer")
        j = self.run_one(fail)
        self.assertEqual((j["state"], j["error"]), ("failed", "OpenAlex did not answer"))

    def test_no_job_starts_while_not_ready(self):
        with tempfile.TemporaryDirectory() as d:
            store = jobs.Store(Path(d))
            i = store.submit("q", [])
            stop = threading.Event()
            checks = []

            def ready():
                checks.append(1)
                if len(checks) >= 2:
                    stop.set()
                return False
            jobs.work(store, lambda q, n: {}, stop, idle=0, ready=ready)
            self.assertEqual(store.get(i)["state"], "queued")

    def test_any_other_failure_shows_nothing_of_itself(self):
        def crash(q, n):
            raise ValueError(f"bad input {q}")
        self.assertEqual(self.run_one(crash)["error"], "internal error")


if __name__ == "__main__":
    unittest.main()
