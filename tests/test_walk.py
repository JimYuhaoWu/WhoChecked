"""
tests/test_walk.py
------------------
The OpenAlex walk and the report, offline. OpenAlex is replaced by invented
responses: no real query is a fixture here, because a query is not ours.

    python -m unittest discover tests
"""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from whochecked import openalex
from whochecked.report import overlap_rows, render


def work(n, names, title="A title", year=2024):
    return {"id": f"https://openalex.org/W{n}", "doi": None, "title": title,
            "publication_year": year, "type": "article",
            "authorships": [{"author": {"display_name": a}} for a in names]}


PRIMARY = work(1, ["Tam Xu", "Kofi Osei", "Mia Brandt"])


class ParseQuery(unittest.TestCase):

    def test_doi_forms(self):
        for q in ("10.0000/example.1", " https://doi.org/10.0000/example.1 ",
                  "doi:10.0000/example.1"):
            self.assertEqual(openalex.parse_query(q), ("doi", "10.0000/example.1"))

    def test_arxiv_ids_resolve_as_their_doi(self):
        for q in ("9912.12345", "9912.12345v2", "arXiv:9912.12345"):
            self.assertEqual(openalex.parse_query(q),
                             ("doi", "10.48550/arXiv.9912.12345"))

    def test_anything_else_is_a_title(self):
        self.assertEqual(openalex.parse_query("A model of things"),
                         ("title", "A model of things"))


class Resolve(unittest.TestCase):

    def test_title_is_reported_as_title(self):
        with mock.patch.object(openalex, "_get",
                               return_value={"results": [PRIMARY]}) as g:
            self.assertEqual(openalex.resolve("Things, and more things"),
                             (PRIMARY, "title"))
        self.assertNotIn(",", g.call_args.args[0]["filter"])

    def test_unresolved_doi_is_none_and_never_falls_back_to_title(self):
        with mock.patch.object(openalex, "_get",
                               return_value={"results": []}) as g:
            self.assertEqual(openalex.resolve("10.0000/absent"), (None, "doi"))
        self.assertEqual(g.call_count, 1)


class CitingWorks(unittest.TestCase):

    def test_pages_until_total(self):
        pages = [{"results": [work(2, [])] * 200, "meta": {"count": 300}},
                 {"results": [work(2, [])] * 100, "meta": {"count": 300}}]
        with mock.patch.object(openalex, "_get", side_effect=pages), \
             mock.patch.object(openalex.time, "sleep"):
            works, total = openalex.citing_works("W1")
        self.assertEqual((len(works), total), (300, 300))

    def test_stops_at_the_page_cap_and_reports_the_total(self):
        page = {"results": [work(2, [])] * 200, "meta": {"count": 20000}}
        with mock.patch.object(openalex, "_get", return_value=page), \
             mock.patch.object(openalex.time, "sleep"):
            works, total = openalex.citing_works("W1")
        self.assertEqual((len(works), total), (200 * openalex.MAX_PAGES, 20000))

    def test_cache_round_trip(self):
        page = {"results": [work(2, ["Ana Lund"])], "meta": {"count": 1}}
        with tempfile.TemporaryDirectory() as d, \
             mock.patch.object(openalex, "_get", return_value=page) as g:
            first = openalex.cached_citing("W1", Path(d))
            second = openalex.cached_citing("W1", Path(d))
        self.assertEqual(first, second)
        self.assertEqual(g.call_count, 1)


class Report(unittest.TestCase):

    def test_rows_carry_fraction_and_shared_names(self):
        rows = overlap_rows(openalex.authors(PRIMARY),
                            [work(2, ["T. Xu", "Ana Lund", "Chidi Okafor"])])
        r = rows[0]
        self.assertEqual((r["verdict"], r["n_shared"], r["n_authors"], r["shared"]),
                         ("partial", 1, 3, ["T. Xu"]))

    def test_missing_author_list_is_unknown(self):
        rows = overlap_rows(openalex.authors(PRIMARY), [work(2, [])])
        self.assertEqual(rows[0]["verdict"], "unknown")

    def test_render_shows_what_is_missing(self):
        rows = overlap_rows([], [work(2, ["Ana Lund"])])
        text = render(work(1, []), "title", rows, 5)
        self.assertIn("TITLE SEARCH", text)
        self.assertIn("No author list", text)
        self.assertIn("The other 4 were not read", text)
        self.assertIn("unknown 1", text)


if __name__ == "__main__":
    unittest.main()
