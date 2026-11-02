"""
scripts/reference_gaps.py
-------------------------
How often OpenAlex holds no reference list for a work, by where it is published.

A work with no reference list in OpenAlex cites nothing there, so it is in no
`cites:` result and no walk can find it, however squarely it evaluates the
resource. CFCR met this as DART-Eval, whose record lists one reference. The
walk cannot see these works, so it can only say how large the blind spot is
likely to be; this measures that, for the report to quote (ROADMAP M2).

Counted over 2020-2025 articles, preprints and reviews, in two populations:
every such work, and those cited at least 5 times. The first includes
editorials, abstracts and other works that genuinely cite nothing; the second
is mostly research, but leans toward older works, since a recent one has had
little time to be cited. Neither is the population of evaluations, which has no
list to count; together they bracket it.

    python scripts/reference_gaps.py

About a dozen requests, within the keyless budget.
"""

from __future__ import annotations

import sys

from whochecked import openalex

BASE = "publication_year:2020-2025,type:article|preprint|review"
POPULATIONS = (("all", ""), ("cited 5+", ",cited_by_count:>4"))
MEASURES = (("", "works"), (",referenced_works_count:0", "no references"),
            (",referenced_works_count:<5", "fewer than 5"))


def counts(flt: str) -> dict[str, int]:
    """Works per venue type, with works that have no venue as "none"."""
    d = openalex._get({"filter": flt, "group_by": "primary_location.source.type"})
    out = {g["key_display_name"]: g["count"] for g in d["group_by"]}
    none = openalex._get({"filter": flt + ",primary_location.source.type:null",
                          "per-page": 1, "select": "id"})
    out["none"] = none["meta"]["count"]
    return out


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    for name, pop in POPULATIONS:
        got = [counts(BASE + pop + m) for m, _ in MEASURES]
        print(f"\n{name}: venue type, works, % with no references, "
              f"% with fewer than 5")
        for venue in sorted(got[0], key=lambda v: -got[0][v]):
            n = got[0][venue]
            print(f"  {venue:<15} {n:>10}  {got[1].get(venue, 0) / n:>6.1%}  "
                  f"{got[2].get(venue, 0) / n:>6.1%}")
    print(f"\nOpenAlex requests: {openalex.requests_sent}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
