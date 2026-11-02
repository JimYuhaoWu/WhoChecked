"""
whochecked/overlap.py
---------------------
Author overlap between a resource's primary paper and a paper that evaluates
it. This is the derivation WhoChecked and CFCR share: one copy, here, because
two would be the worst possible thing to let drift.

Authors are compared normalized to lastname + first initial:

  either author list empty                            -> unknown
  shared == 0                                         -> independent
  0 < shared < 50% of the evaluating paper's authors  -> partial
  shared >= 50%                                       -> same-group

A match on that key is only as strong as the names behind it, so `weak_match`
names what each match rests on. It flags; it does not reclassify. Dropping a
match it suspects would be the tool deciding two people are different, which
is a conclusion the metadata does not support either way.
"""

from __future__ import annotations

import re
import unicodedata

# Fraction of the EVALUATING paper's authors that may be shared with the primary
# paper before the evaluation is treated as coming from the same group.
PARTIAL_MAX = 0.50


def _tokens(name: str) -> list[str]:
    n = unicodedata.normalize("NFKD", name)
    n = "".join(c for c in n if not unicodedata.combining(c)).lower()
    return [p for p in re.split(r"[\s.\-,]+", n) if p]


def norm_author(name: str) -> str:
    """
    Normalize to `lastname|first-initial`, accent- and case-folded.

    Deliberately lossy and therefore conservative: two different people who
    share a surname and initial collide, which counts as author overlap and
    biases the derivation toward the LOWER (less independent) result. Reporting
    a resource as less independently evaluated than it is, is the safe direction.
    """
    parts = _tokens(name)
    if not parts:
        return ""
    return f"{parts[-1]}|{parts[0][0]}"


# A surname this short is shared by enough people that surname + initial says
# little about who someone is.
SHORT_SURNAME = 2


def weak_match(a: str, b: str) -> list[str]:
    """
    Why a match between two names with the same `norm_author` key is weak,
    or [] when nothing weakens it beyond the key itself:

      "initial only"      one side gives only an initial, so the forename
                          cannot be compared
      "short surname"     the surname is SHORT_SURNAME letters or fewer
      "forenames differ"  both give a full forename and they are not the same
                          (a nickname or a second person: the metadata cannot
                          tell which)
    """
    ta, tb = _tokens(a), _tokens(b)
    reasons = []
    if len(ta[0]) == 1 or len(tb[0]) == 1:
        reasons.append("initial only")
    elif ta[0] != tb[0]:
        reasons.append("forenames differ")
    if len(ta[-1]) <= SHORT_SURNAME:
        reasons.append("short surname")
    return reasons


def classify_overlap(primary: set[str], evaluating: set[str]) -> tuple[str, set[str]]:
    # An author list we do not have is unknown, never independent: an empty set
    # shares nothing with anything, which would otherwise read as the strongest
    # possible evidence from the weakest possible data.
    #
    # "" is what norm_author returns for a name with nothing in it. It is not an
    # author: left in, two such names would count as one shared author, and a
    # list of nothing else would hide that the list is effectively empty.
    primary = primary - {""}
    evaluating = evaluating - {""}
    shared = primary & evaluating
    if not primary or not evaluating:
        return "unknown", shared
    if not shared:
        return "independent", shared
    if len(shared) / len(evaluating) < PARTIAL_MAX:
        return "partial", shared
    return "same-group", shared
