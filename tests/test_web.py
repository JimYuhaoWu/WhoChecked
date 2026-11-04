"""
tests/test_web.py
-----------------
The server's pages, offline: OpenAlex is never called, and every query is
invented.

    python -m unittest discover tests
"""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from whochecked import jobs, openalex, web

QUERY = "10.0000/example.private"


def work(n, title, names, abstract=None):
    return {"id": f"https://openalex.org/W{n}", "doi": None, "title": title,
            "publication_year": 2024, "type": "article",
            "authorships": [{"author": {"display_name": a}} for a in names],
            "abstract_inverted_index": ({w: [i] for i, w in enumerate(abstract.split())}
                                        if abstract else None)}


PRIMARY = work(1, "A widget model", ["Ana Lund", "Kofi Osei"])
CITING = [work(2, "Benchmarking widget models", ["Tom Xu"], "we compare tools"),
          work(3, "<script>alert(1)</script> fails", ["A. Lund", "Mia Brandt"]),
          work(4, "Rivers", ["Kwame Osei"], "about rivers")]


class Web(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = jobs.Store(Path(self.tmp.name))
        self.client = web.create_app(self.store).test_client()

    def tearDown(self):
        self.tmp.cleanup()

    def submit(self, query=QUERY, names=""):
        return self.client.post("/jobs", data={"query": query, "names": names})

    def finish(self, primary=PRIMARY, citing=CITING):
        job_id = self.store.next_queued()
        with mock.patch.object(openalex, "resolve", return_value=(primary, "doi")), \
             mock.patch.object(openalex, "cached_citing", return_value=(citing, 3)):
            job = self.store.get(job_id)
            self.store.finish(job_id, result=web.run(Path(self.tmp.name))(
                job["query"], job["names"]))
        return job_id

    def test_query_is_in_no_url(self):
        r = self.submit()
        self.assertEqual(r.status_code, 303)
        self.assertRegex(r.headers["Location"], r"^/r/[A-Za-z0-9_-]{22}$")
        self.assertNotIn("example", r.headers["Location"])

    def test_headers_on_every_page(self):
        for r in (self.client.get("/"), self.client.get("/help"), self.submit(),
                  self.client.get("/r/" + "a" * 22)):
            self.assertEqual(r.headers["Referrer-Policy"], "no-referrer")
            self.assertEqual(r.headers["Cache-Control"], "no-store")
            self.assertNotIn("Set-Cookie", r.headers)

    def test_landing_shows_licence_and_example(self):
        text = self.client.get("/").get_data(as_text=True)
        self.assertIn("MIT licence", text)
        self.assertIn(web.EXAMPLES[0]["query"], text)

    def test_empty_and_long_queries_are_refused(self):
        self.assertEqual(self.submit("  ").status_code, 400)
        self.assertEqual(self.submit("x" * (web.MAX_QUERY + 1)).status_code, 400)
        self.assertEqual(list(Path(self.tmp.name).glob("*.json")), [])

    def test_pending_page_refreshes_and_survives_a_reload(self):
        loc = self.submit().headers["Location"]
        for _ in range(2):
            text = self.client.get(loc).get_data(as_text=True)
            self.assertIn("Queued", text)
            self.assertIn('http-equiv="refresh"', text)

    def test_report(self):
        loc = self.submit(names="Widgetron").headers["Location"]
        self.finish()
        r = self.client.get(loc)
        text = r.get_data(as_text=True)
        self.assertNotIn('http-equiv="refresh"', text)
        self.assertIn("A widget model", text)
        self.assertIn("Benchmarking widget models", text)
        self.assertIn("A. Lund", text)
        self.assertIn("(weak: initial only)", text)
        self.assertIn("cannot appear below", text)

    def test_titles_are_escaped(self):
        loc = self.submit().headers["Location"]
        self.finish()
        text = self.client.get(loc).get_data(as_text=True)
        self.assertNotIn("<script>alert(1)</script>", text)
        self.assertIn("&lt;script&gt;", text)

    def test_not_found_is_unknown_not_absent(self):
        loc = self.submit().headers["Location"]
        job_id = self.store.next_queued()
        with mock.patch.object(openalex, "resolve", return_value=(None, "doi")):
            self.store.finish(job_id, result=web.run(Path(self.tmp.name))(QUERY, []))
        text = self.client.get(loc).get_data(as_text=True)
        self.assertIn("says nothing about whether the paper exists", text)

    def test_a_failed_fetch_shows_its_message(self):
        loc = self.submit().headers["Location"]
        job_id = self.store.next_queued()
        with mock.patch.object(openalex, "resolve",
                               side_effect=openalex.FetchError("no answer")):
            with self.assertRaises(jobs.FailedJob):
                web.run(Path(self.tmp.name))(QUERY, [])
        self.store.finish(job_id, error="no answer")
        text = self.client.get(loc).get_data(as_text=True)
        self.assertIn("no answer", text)
        self.assertIn("Try again", text)

    def test_submissions_past_the_hourly_limit_are_refused(self):
        for _ in range(web.JOBS_PER_HOUR):
            self.assertEqual(self.submit().status_code, 303)
        r = self.submit()
        self.assertEqual(r.status_code, 429)
        self.assertEqual(r.headers["Retry-After"], "3600")
        self.assertIn("Try again in 60 minutes", r.get_data(as_text=True))
        self.assertEqual(len(list(Path(self.tmp.name).glob("*.json"))),
                         web.JOBS_PER_HOUR)

    def test_the_limit_is_announced(self):
        self.assertIn(f"at most {web.JOBS_PER_HOUR} new checks",
                      self.client.get("/").get_data(as_text=True))
        self.assertIn('id="limits"', self.client.get("/help").get_data(as_text=True))

    def test_a_queued_job_says_when_a_spent_budget_resets(self):
        loc = self.submit().headers["Location"]
        resets = openalex.datetime(2026, 1, 1, 0, 0, tzinfo=openalex.timezone.utc)
        with mock.patch.object(openalex, "budget_allows", return_value=False),              mock.patch.object(openalex, "budget_resets", resets):
            text = self.client.get(loc).get_data(as_text=True)
        self.assertIn("no check starts until it resets, at about 00:00 UTC", text)
        self.assertNotIn("until it resets", self.client.get(loc).get_data(as_text=True))

    def test_unknown_and_malformed_ids_are_404(self):
        for path in ("/r/" + "a" * 22, "/r/..%2F..%2Fetc", "/r/x"):
            self.assertEqual(self.client.get(path).status_code, 404)


if __name__ == "__main__":
    unittest.main()
