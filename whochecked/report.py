"""
whochecked/report.py
--------------------
Each work citing a primary paper, with how much it reads like an evaluation and
its author overlap with the primary paper, and the text report of them.

The score ranks and the sections are boundaries for a reader. Nothing is
dropped: a work scoring zero is counted, and listed with --all.
"""

from __future__ import annotations

from whochecked.openalex import authors, short_id
from whochecked.overlap import classify_overlap, norm_author, weak_match
from whochecked.score import score

VERDICTS = ("independent", "partial", "same-group", "unknown")

MATCHING_RULE = (
    "Authors are matched on surname + first initial, accent- and case-folded. "
    "This is lossy: two different people who share both count as overlap, and "
    "a name written surname-first (\"Xu T\") does not match the same name "
    "written given-first (\"Tam Xu\"). A shared author marked weak matched "
    "on an initial alone, on a surname of two letters or fewer, or with "
    "forenames or middle initials that differ; the overlap counts it either "
    "way.")

SCORING_RULE = (
    "The score counts benchmark and critique words, a title hit outweighing an "
    "abstract hit, and demotes reviews and errata. It ranks; it does not say "
    "which works are evaluations. The words are English: a paper in another "
    "language scores zero, and that zero means unknown.")


# Share of 2020-2025 articles, preprints and reviews with no reference list in
# OpenAlex, by venue type: (all such works, those cited 5+ times). A snapshot,
# so it costs a report nothing; scripts/reference_gaps.py measures it again.
REFERENCE_GAPS_MEASURED = "2026-11-02"
REFERENCE_GAPS = {"journal": (0.342, 0.027),
                  "repository (preprints)": (0.822, 0.443),
                  "conference": (0.528, 0.149),
                  "no venue recorded": (0.855, 0.533)}

GAP_RULE = (
    "A work OpenAlex holds no reference list for cites nothing there, so it "
    "cannot appear below however squarely it evaluates this paper. Share of "
    "2020-2025 works with no reference list, of all works / of works cited 5+ "
    f"times (OpenAlex, measured {REFERENCE_GAPS_MEASURED}): "
    + "; ".join(f"{v} {a:.0%} / {c:.0%}" for v, (a, c) in REFERENCE_GAPS.items())
    + ". Evaluations published only as preprints or conference papers are the "
    "likeliest to be missing.")


def build_rows(primary_authors: list[str], citing: list[dict],
               name_forms: set[str]) -> list[dict]:
    by_key = {}
    for a in primary_authors:
        by_key.setdefault(norm_author(a), []).append(a)
    primary = set(by_key)
    rows = []
    for w in citing:
        names = authors(w)
        keys = {norm_author(a) for a in names} - {""}
        kind, shared = classify_overlap(primary, keys)
        # Against the primary name it matches most strongly: a primary list
        # can carry the same person twice, once with an initial.
        weak = {}
        for a in names:
            if norm_author(a) in shared:
                reasons = min((weak_match(p, a) for p in by_key[norm_author(a)]),
                              key=len)
                if reasons:
                    weak[a] = reasons
        rows.append({"id": short_id(w),
                     "doi": w.get("doi"),
                     "title": w.get("title"),
                     "year": w.get("publication_year"),
                     "verdict": kind,
                     "n_shared": len(shared),
                     "n_authors": len(keys),
                     "shared": [a for a in names if norm_author(a) in shared],
                     "weak": weak,
                     **score(w, name_forms)})
    return rows


def sections(rows: list[dict]) -> dict[str, list[dict]]:
    """
    Ranked, title-only and zero, each ranked by score.

    Works OpenAlex holds no abstract for are ranked apart: scored on a title
    alone, they sink below everything that has an abstract, and CFCR found a
    real critique at 102nd of 132 that way and 6th of 8 once separated.
    """
    ranked = sorted(rows, key=lambda r: -r["score"])
    return {"ranked": [r for r in ranked if r["score"] > 0 and r["has_abstract"]],
            "title_only": [r for r in ranked if r["score"] > 0 and not r["has_abstract"]],
            "zero": [r for r in ranked if r["score"] <= 0]}


def overlap_counts(rows: list[dict]) -> tuple[dict[str, int], int]:
    """Works per verdict, and the partial and same-group works whose shared
    authors are all marked weak."""
    counts = {v: sum(r["verdict"] == v for r in rows) for v in VERDICTS}
    n_weak = sum(r["verdict"] in ("partial", "same-group")
                 and len(r["weak"]) == len(r["shared"]) for r in rows)
    return counts, n_weak


def _row(r: dict) -> list[str]:
    frac = (f"{r['n_shared']}/{r['n_authors']}" if r["verdict"] != "unknown"
            else "-")
    out = [f"{r['score']:>6.2f}  {r['verdict']:<12} {frac:>7}  "
           f"{r['year'] or '----'}  {r['id']}  {r['title'] or '(no title)'}"]
    if r["parts"]:
        out.append(f"{'':<8}score: " + ", ".join(f"{k} {v:+g}"
                                                for k, v in r["parts"].items()))
    if r["terms"]:
        out.append(f"{'':<8}words: {', '.join(r['terms'])}")
    if r["shared"]:
        out.append(f"{'':<8}shared authors: " + ", ".join(
            f"{a} (weak: {', '.join(r['weak'][a])})" if a in r["weak"] else a
            for a in r["shared"]))
    return out


def render(primary: dict, how: str, rows: list[dict], total: int,
           name_forms: set[str] = frozenset(), dropped: list[str] = (),
           show_all: bool = False) -> str:
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
    if name_forms:
        out.append(f"         Resource name scored: {', '.join(sorted(name_forms))}")
    if dropped:
        out.append(f"         Not scored, shorter than 4 characters: {', '.join(dropped)}")

    out += ["", f"Citing works: {total} in OpenAlex, {len(rows)} read."]
    if len(rows) < total:
        out.append(f"Only the first {len(rows)} were read. The other "
                   f"{total - len(rows)} are unknown, not absent.")
    out += [GAP_RULE, SCORING_RULE, MATCHING_RULE, ""]

    counts, n_weak = overlap_counts(rows)
    out.append("Author overlap: " + " | ".join(f"{v} {counts[v]}" for v in VERDICTS))
    out.append("  (unknown: an author list is missing on one side)")
    out.append(f"  {n_weak} of the partial and same-group works share only "
               f"authors marked weak")

    s = sections(rows)
    out += ["", f"== Scored above zero: {len(s['ranked'])} ==",
            "   score  overlap      shared  year  id  title"]
    for r in s["ranked"]:
        out += _row(r)
    out += ["", f"== Scored above zero on the title alone, OpenAlex has no "
                f"abstract: {len(s['title_only'])} =="]
    for r in s["title_only"]:
        out += _row(r)
    n_no_abs = sum(not r["has_abstract"] for r in s["zero"])
    out += ["", f"== Scored zero or below: {len(s['zero'])}, of which "
                f"{n_no_abs} have no abstract and were read on the title alone =="]
    if show_all:
        for r in s["zero"]:
            out += _row(r)
    else:
        out.append("   Not listed. --all lists them.")
    return "\n".join(out)
