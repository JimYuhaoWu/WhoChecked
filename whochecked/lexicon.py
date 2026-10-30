"""
whochecked/lexicon.py
---------------------
The evaluation lexicon: the words that make a citing work read like a benchmark
or a critique of what it cites. WhoChecked owns it and CFCR imports it, for the
reason whochecked.overlap is shared -- two copies of a scoring table drift, and
CFCR measures its triage against this one.

Field-agnostic on purpose. Nothing here names a discipline, a method or a kind
of resource; CFCR's genomics terms (model classes, scope tables) stay in CFCR.

The terms and weights are CFCR's as measured, unchanged, so CFCR's recorded
numbers still describe them. What each was measured against is in CFCR's
docs/triage_design.md, section 2.2:
https://github.com/JimYuhaoWu/cell_fate_control_resources/blob/main/docs/triage_design.md

English only. A paper written in another language matches nothing, and that
zero means unknown, not "not an evaluation".
"""

from __future__ import annotations

import re

BENCH_TITLE = [
    "benchmark", "benchmarking", "evaluation", "evaluating", "evaluate",
    "comparison", "comparative", "compare", "assessment", "assessing", "assess",
    "baseline", "leaderboard", "head-to-head", "systematic",
]
BENCH_ABSTRACT = BENCH_TITLE + [
    "we evaluate", "we compare", "we benchmark", "we assess", "across models",
    "evaluated on", "four state-of-the-art", "three state-of-the-art",
]
CRIT_TITLE = [
    "fail", "fails", "struggle", "struggles", "poorly", "overestimat",
    "underestimat", "limitation", "caveat", "cannot", "pitfall", "overstate",
    "illusion", "spurious", "confound", "underperform", "inflated",
    "misleading", "hard to compare", "not generalize", "questioning",
    "reassess", "overlooked",
]
CRIT_ABSTRACT = CRIT_TITLE + [
    "fails to", "struggle to", "poorly explained", "limited performance",
    "no better than", "worse than", "artifact", "remains unexplored",
    "often fail", "incorrect direction",
]
# These demote rather than exclude: a review that evaluates what it cites is
# still worth a reader's glance.
DEMOTE_TITLE = ["review", "perspective", "primer", "roadmap", "erratum",
                "correction", "retraction"]


def hits(terms, text: str) -> list[str]:
    """Terms present in `text`, left-anchored on a word boundary."""
    return [t for t in terms if re.search(r"(?<![a-z])" + re.escape(t), text)]


def names(forms: set[str], text: str) -> bool:
    return any(re.search(r"(?<![a-z0-9])" + re.escape(f.lower()) + r"(?![a-z0-9])", text)
               for f in forms)


def lexicon(title: str, abstract: str) -> tuple[float, float]:
    """(benchmark, critique) for lower-cased text. A title hit outweighs an
    abstract hit, and critique terms outweigh benchmark ones because critiques
    are rarer."""
    bench = (min(2.0 * len(hits(BENCH_TITLE, title)), 4.0)
             + min(0.5 * len(hits(BENCH_ABSTRACT, abstract)), 2.0))
    crit = (min(2.5 * len(hits(CRIT_TITLE, title)), 5.0)
            + min(0.75 * len(hits(CRIT_ABSTRACT, abstract)), 3.0))
    return bench, crit
