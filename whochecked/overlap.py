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
"""

from __future__ import annotations

import re
import unicodedata

# Fraction of the EVALUATING paper's authors that may be shared with the primary
# paper before the evaluation is treated as coming from the same group.
PARTIAL_MAX = 0.50


def norm_author(name: str) -> str:
    """
    Normalize to `lastname|first-initial`, accent- and case-folded.

    Deliberately lossy and therefore conservative: two different people who
    share a surname and initial collide, which counts as author overlap and
    biases the derivation toward the LOWER (less independent) result. Reporting
    a resource as less independently evaluated than it is, is the safe direction.
    """
    n = unicodedata.normalize("NFKD", name)
    n = "".join(c for c in n if not unicodedata.combining(c)).lower()
    parts = [p for p in re.split(r"[\s.\-,]+", n) if p]
    if not parts:
        return ""
    return f"{parts[-1]}|{parts[0][0]}"


def classify_overlap(primary: set[str], evaluating: set[str]) -> tuple[str, set[str]]:
    # An author list we do not have is unknown, never independent: an empty set
    # shares nothing with anything, which would otherwise read as the strongest
    # possible evidence from the weakest possible data.
    shared = primary & evaluating
    if not primary or not evaluating:
        return "unknown", shared
    if not shared:
        return "independent", shared
    if len(shared) / len(evaluating) < PARTIAL_MAX:
        return "partial", shared
    return "same-group", shared
