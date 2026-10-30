"""
tests/test_score.py
-------------------
The evaluation score and the ranked report, offline, on invented works.

    python -m unittest discover tests
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from whochecked import openalex
from whochecked.lexicon import lexicon
from whochecked.report import build_rows, render, sections
from whochecked.score import score, usable_names


def work(n, title, abstract=None, kind="article", names=("Ana Lund",)):
    inv = ({w: [i] for i, w in enumerate(abstract.split())} if abstract
           else None)
    return {"id": f"https://openalex.org/W{n}", "doi": None, "title": title,
            "publication_year": 2024, "type": kind,
            "authorships": [{"author": {"display_name": a}} for a in names],
            "abstract_inverted_index": inv}


class Lexicon(unittest.TestCase):

    def test_title_outweighs_abstract(self):
        self.assertEqual(lexicon("a benchmark", ""), (2.0, 0.0))
        self.assertEqual(lexicon("", "a benchmark"), (0.5, 0.0))

    def test_caps(self):
        bench, _ = lexicon("benchmark evaluation comparison assessment baseline", "")
        self.assertEqual(bench, 4.0)


class Score(unittest.TestCase):

    def test_breakdown_and_words(self):
        s = score(work(1, "Comparative tools", "five tools are listed"), set())
        self.assertEqual(s["parts"], {"bench": 2.0})
        self.assertEqual(s["terms"], ["comparative"])
        self.assertTrue(s["has_abstract"])

    def test_one_word_can_hit_several_terms(self):
        # Matching is anchored on the left only, so a word hits every term it
        # starts with. CFCR's weights were measured with this, so it is kept.
        s = score(work(1, "Benchmarking tools", "we compare five tools"), set())
        self.assertEqual(s["parts"], {"bench": 5.0})
        self.assertEqual(s["terms"], ["benchmark", "benchmarking", "compare",
                                      "we compare"])

    def test_critique(self):
        s = score(work(1, "Why the method struggled"), set())
        self.assertEqual(s["parts"], {"crit": 2.5})
        self.assertFalse(s["has_abstract"])

    def test_name_scores_only_when_given(self):
        w = work(1, "Applying Widgetron to rivers")
        self.assertEqual(score(w, set())["score"], 0)
        self.assertEqual(score(w, {"Widgetron"})["parts"], {"name_title": 3.0})

    def test_name_is_word_bounded(self):
        self.assertEqual(score(work(1, "Widgetronic rivers"), {"Widgetron"})["score"], 0)

    def test_reviews_demote(self):
        s = score(work(1, "A review of evaluation", kind="review"), set())
        self.assertEqual(s["parts"],
                         {"bench": 2.0, "demote_title": -3.0, "demote_type": -3.0})

    def test_short_names_are_dropped(self):
        self.assertEqual(usable_names(["WT", "Widgetron"]), ({"Widgetron"}, ["WT"]))


class Abstract(unittest.TestCase):

    def test_flatten_orders_by_position(self):
        w = {"abstract_inverted_index": {"b": [1], "a": [0, 2]}}
        self.assertEqual(openalex.flatten_abstract(w), "a b a")

    def test_none_when_absent(self):
        self.assertIsNone(openalex.flatten_abstract({"abstract_inverted_index": None}))

    def test_cache_from_other_fields_is_a_miss(self):
        page = {"results": [], "meta": {"count": 0}}
        with tempfile.TemporaryDirectory() as d, \
             mock.patch.object(openalex, "_get", return_value=page) as g:
            Path(d, "citing_W1.json").write_text(json.dumps(
                {"select": "id,title", "total": 0, "citing": []}))
            openalex.cached_citing("W1", Path(d))
        self.assertEqual(g.call_count, 1)


class Report(unittest.TestCase):

    CITING = [work(2, "Benchmarking tools", "we compare tools"),
              work(3, "Tools fail", None),
              work(4, "Rivers", "about rivers"),
              work(5, "Comparison", "x")]

    def test_sections(self):
        s = sections(build_rows([], self.CITING, set()))
        self.assertEqual([r["id"] for r in s["ranked"]], ["W2", "W5"])
        self.assertEqual([r["id"] for r in s["title_only"]], ["W3"])
        self.assertEqual([r["id"] for r in s["zero"]], ["W4"])

    def test_zero_is_counted_and_listed_only_with_all(self):
        rows = build_rows(["Ana Lund"], self.CITING, set())
        primary = work(1, "P", names=("Ana Lund",))
        self.assertNotIn("W4", render(primary, "doi", rows, 4))
        self.assertIn("Scored zero or below: 1", render(primary, "doi", rows, 4))
        self.assertIn("W4", render(primary, "doi", rows, 4, show_all=True))


if __name__ == "__main__":
    unittest.main()
