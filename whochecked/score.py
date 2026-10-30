"""
whochecked/score.py
-------------------
How much a citing work reads like an evaluation of what it cites, with the
breakdown. A score ranks; it does not classify. There is no ground truth for
"this citing work is an evaluation", so nothing here says one is.

CFCR's scorer also counts signals that need a catalogue -- other catalogued
models named, other catalogued primaries cited -- and its strongest, "cites the
primary paper", is true of every work WhoChecked walks. None of those are here.
"""

from __future__ import annotations

from whochecked.lexicon import (BENCH_ABSTRACT, BENCH_TITLE, CRIT_ABSTRACT,
                                CRIT_TITLE, DEMOTE_TITLE, hits, lexicon, names)
from whochecked.openalex import flatten_abstract

# A name this short matches almost everything, so it is not used: CFCR's alias
# lists held "NT", which is in nearly every abstract.
MIN_NAME = 4


def usable_names(given: list[str]) -> tuple[set[str], list[str]]:
    """(forms used, forms dropped as too short)."""
    return ({n for n in given if len(n) >= MIN_NAME},
            [n for n in given if len(n) < MIN_NAME])


def score(work: dict, name_forms: set[str]) -> dict:
    title = (work.get("title") or "").lower()
    abstract = (flatten_abstract(work) or "").lower()
    bench, crit = lexicon(title, abstract)
    parts = {"bench": bench, "crit": crit}
    # Naming the resource is the best evidence a paper is about it rather than
    # citing it for one of many reasons. Only when the user gave a name.
    if name_forms and names(name_forms, title):
        parts["name_title"] = 3.0
    elif name_forms and names(name_forms, abstract):
        parts["name_abstract"] = 1.5
    if hits(DEMOTE_TITLE, title):
        parts["demote_title"] = -3.0
    if (work.get("type") or "") == "review":
        parts["demote_type"] = -3.0
    terms = sorted(set(hits(BENCH_TITLE + CRIT_TITLE, title))
                   | set(hits(BENCH_ABSTRACT + CRIT_ABSTRACT, abstract)))
    return {"score": round(sum(parts.values()), 2),
            "parts": {k: v for k, v in parts.items() if v},
            "terms": terms,
            "has_abstract": bool(abstract)}
