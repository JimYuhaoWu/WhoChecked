"""
whochecked/report.py
--------------------
Author overlap between a primary paper and each work citing it, and the text
report of it. Every citing work is listed and none is ranked: nothing here yet
scores which citing works are evaluations, and a citation is not one.
"""

from __future__ import annotations

from whochecked.openalex import authors, short_id
from whochecked.overlap import classify_overlap, norm_author

VERDICTS = ("independent", "partial", "same-group", "unknown")

MATCHING_RULE = (
    "Authors are matched on surname + first initial, accent- and case-folded. "
    "This is lossy: two different people who share both count as overlap, and "
    "a name written surname-first (\"Xu T\") does not match the same name "
    "written given-first (\"Tam Xu\").")


def overlap_rows(primary_authors: list[str], citing: list[dict]) -> list[dict]:
    primary = {norm_author(a) for a in primary_authors}
    rows = []
    for w in citing:
        names = authors(w)
        keys = {norm_author(a) for a in names} - {""}
        kind, shared = classify_overlap(primary, keys)
        rows.append({"id": short_id(w),
                     "title": w.get("title"),
                     "year": w.get("publication_year"),
                     "verdict": kind,
                     "n_shared": len(shared),
                     "n_authors": len(keys),
                     "shared": [a for a in names if norm_author(a) in shared]})
    return rows


def render(primary: dict, how: str, rows: list[dict], total: int) -> str:
    p_authors = authors(primary)
    out = [f"Primary: {primary.get('title')} ({primary.get('publication_year')})",
           f"         {primary.get('doi') or primary['id']}"]
    if how == "title":
        out.append("         Found by TITLE SEARCH, which is a best guess: "
                   "check this is the paper you meant.")
    if p_authors:
        out.append(f"         {len(p_authors)} authors")
    else:
        out.append("         No author list in OpenAlex, so overlap cannot be "
                   "computed: every citing work below is unknown.")

    out += ["", f"Citing works: {total} in OpenAlex, {len(rows)} listed."]
    if len(rows) < total:
        out.append(f"Only the first {len(rows)} are listed. The other "
                   f"{total - len(rows)} were not read, so they are unknown, "
                   "not absent.")
    out += ["A citing work is not an evaluation. Nothing here says which of "
            "these evaluated the resource.",
            MATCHING_RULE, ""]

    counts = {v: sum(r["verdict"] == v for r in rows) for v in VERDICTS}
    out.append("Author overlap: " + " | ".join(f"{v} {counts[v]}" for v in VERDICTS))
    out.append("  (unknown: an author list is missing on one side)")
    out.append("")

    for r in rows:
        frac = (f"{r['n_shared']}/{r['n_authors']}" if r["verdict"] != "unknown"
                else "-")
        out.append(f"{r['verdict']:<12} {frac:>7}  {r['year'] or '----'}  "
                   f"{r['id']}  {r['title'] or '(no title)'}")
        if r["shared"]:
            out.append(f"{'':<22}shared: {', '.join(r['shared'])}")
    return "\n".join(out)
