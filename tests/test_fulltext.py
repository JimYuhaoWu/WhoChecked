"""
tests/test_fulltext.py
----------------------
Reading a supplied paper, offline. Every paper, author and DOI is invented.

    python -m unittest discover tests
"""

import unittest

from whochecked import fulltext

PRIMARY = [{"n": 1, "doi": "https://doi.org/10.0000/widget.1",
            "title": "Widgetron for fast and sensitive widget profiling",
            "year": 2019, "authors": ["Ana Lund", "Kofi Osei"]}]
ROWS = [{"id": "W2", "doi": "https://doi.org/10.0000/bench.2",
         "title": "Benchmarking widget profiling methods across ten labs"},
        {"id": "W3", "doi": None,
         "title": "A systematic comparison of widget assays in tissue"}]

NUMBERED = """Benchmarking widget profiling methods across ten labs
https://doi.org/10.0000/bench.2
Introduction
Widgets matter. Several assays exist [1, 2]. Widgetron was introduced
recently [3-5]. We followed the kit manual.
Results
We compared Widgetron with two older assays and found it fails on low
input [4]. Other work used chromosome 4 data.
References
1. Doe, J. A first paper. J. Wid. 1, 1 (2001).
2. Roe, R. A second paper. J. Wid. 2, 2 (2002).
3. Poe, P. A third paper. J. Wid. 3, 3 (2003).
4. Lund, A. & Osei, K. Widgetron for fast and sensitive wid-
get profiling. Nat. Wid. 9, 1 (2019).
5. Moe, M. A fifth paper. J. Wid. 5, 5 (2005).
"""

SUPERSCRIPT = """A study
Introduction
Widgetron was reported to be sensitive4. Libraries were made for 4 min.
Results
We measured background as described4,6.
References
1. Doe, J. A first paper. (2001).
2. Roe, R. A second paper. (2002).
3. Poe, P. A third paper. (2003).
4. Lund, A. et al. Widget ron for fast and sen sitive widget proﬁling (2019).
5. Moe, M. A fifth paper. (2005).
6. Zoe, Z. A sixth paper. (2006).
"""

AUTHOR_YEAR = """A study
Methods
Profiles were made with Widgetron (Lund et al., 2019) as described.
References
Doe J. 2001. A first paper.
Lund A, Osei K. 2019. Widgetron for fast and sensitive widget profiling.
"""


def tiny_pdf(lines):
    """A one-page PDF holding `lines` as text, built by hand."""
    body = " T* ".join(f"({ln}) Tj" for ln in lines)
    stream = f"BT /F1 12 Tf 14 TL 72 720 Td {body} ET".encode()
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
            b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    out, offsets = b"%PDF-1.4\n", []
    for i, o in enumerate(objs, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + o + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    out += b"".join(b"%010d 00000 n \n" % o for o in offsets)
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objs) + 1, xref)
    return out


class Extract(unittest.TestCase):

    def test_plain_text_is_one_page(self):
        self.assertEqual(fulltext.extract(b"hello there"),
                         {"state": "read", "pages": ["hello there"], "truncated": False})

    def test_empty_text_is_unreadable(self):
        self.assertEqual(fulltext.extract(b"  \n"), {"state": "unreadable"})

    def test_a_pdf_is_read_in_a_child_process(self):
        got = fulltext.extract(tiny_pdf(["Widgetron line one", "line two"]))
        self.assertEqual(got["state"], "read")
        self.assertIn("Widgetron line one", got["pages"][0])

    def test_a_broken_pdf_fails_without_raising(self):
        self.assertEqual(fulltext.extract(b"%PDF-1.4 nonsense"), {"state": "failed"})


class Match(unittest.TestCase):

    def test_by_doi_on_the_first_page(self):
        row, how, doi = fulltext.match_row([NUMBERED], ROWS)
        self.assertEqual((row["id"], how, doi), ("W2", "doi", "10.0000/bench.2"))

    def test_by_title_is_marked_a_guess(self):
        row, how, _ = fulltext.match_row(
            ["A Systematic Comparison of Widget Assays in Tissue\nby someone"], ROWS)
        self.assertEqual((row["id"], how), ("W3", "title"))

    def test_no_match_keeps_the_doi_it_found(self):
        self.assertEqual(fulltext.match_row(["doi: 10.0000/other.9."], ROWS),
                         (None, None, "10.0000/other.9"))


class Read(unittest.TestCase):

    def test_numbers_and_ranges(self):
        self.assertEqual(fulltext._numbers("3-5, 9"), {3, 4, 5, 9})
        self.assertEqual(fulltext._numbers("1, 2"), {1, 2})

    def test_bracketed_citations_by_number(self):
        ev = fulltext.read([NUMBERED], PRIMARY, set())
        self.assertEqual(ev["reference"]["number"], 4)
        texts = [s["text"] for s in ev["sentences"]]
        self.assertEqual(ev["n_cited"], 2)
        self.assertTrue(any("[3-5]" in t for t in texts))
        self.assertTrue(any("fails on low input" in t for t in texts))
        # "chromosome 4" is not a citation in a paper that cites in brackets.
        self.assertFalse(any("chromosome" in t for t in texts))
        self.assertEqual(ev["scored_on"], "citations")
        self.assertIn("fails", ev["ft_terms"])

    def test_sections_and_pages_are_kept(self):
        ev = fulltext.read([NUMBERED], PRIMARY, set())
        self.assertEqual({(s["page"], s["section"]) for s in ev["sentences"]},
                         {(1, "Introduction"), (1, "Results")})

    def test_a_name_is_found_and_ranked_after_citations(self):
        ev = fulltext.read([NUMBERED], PRIMARY, {"Widgetron"})
        hows = [s["how"] for s in ev["sentences"]]
        self.assertEqual(hows[:2], ["number", "number"])
        self.assertNotIn("number", hows[2:])

    def test_superscripts_are_bare_numbers_shown_as_guesses(self):
        ev = fulltext.read([SUPERSCRIPT], PRIMARY, set())
        self.assertEqual(ev["reference"]["number"], 4)
        hows = {s["text"]: s["how"] for s in ev["sentences"]}
        self.assertEqual(set(hows.values()), {"bare number"})
        self.assertTrue(any("sensitive4" in t for t in hows))
        self.assertTrue(any("described4,6" in t for t in hows))
        self.assertFalse(any("4 min" in t for t in hows))

    def test_author_and_year(self):
        ev = fulltext.read([AUTHOR_YEAR], PRIMARY, set())
        self.assertEqual((ev["reference"]["surname"], ev["reference"]["year"]),
                         ("Lund", 2019))
        self.assertEqual([s["how"] for s in ev["sentences"]], ["author and year"])

    def test_a_missing_reference_is_unknown_and_says_so(self):
        ev = fulltext.read(["Intro\nNothing here.\nReferences\n1. Doe. (2001)."],
                           PRIMARY, set())
        self.assertEqual(ev["reference"], {"found": False, "list_found": True})
        self.assertEqual((ev["n_cited"], ev["n_named"], ev["scored_on"]),
                         (0, 0, None))

    def test_no_reference_list_is_reported(self):
        ev = fulltext.read(["Just text, cited [4]."], PRIMARY, set())
        self.assertFalse(ev["reference"]["list_found"])

    def test_sentences_are_bounded(self):
        many = "Results\n" + " ".join(f"Widgetron run {i} worked." for i in range(40))
        ev = fulltext.read([many], PRIMARY, {"Widgetron"})
        self.assertEqual(ev["n_named"], 40)
        self.assertEqual(len(ev["sentences"]), fulltext.MAX_SENTENCES)
        self.assertEqual(ev["scored_on"], "names")


if __name__ == "__main__":
    unittest.main()
