"""
scripts/measure_against_cfcr.py
-------------------------------
Where the evaluations CFCR's curators found land in WhoChecked's ranking.

CFCR's db/entity_paper.tsv records, for each catalogued model, the `benchmark`
and `critique` papers a curator accepted. For each model, this walks its primary
paper's citing works through WhoChecked and reports which section each curated
evaluation lands in, and at what rank.

What it measures is recall-at-rank, not precision. The curated rows are what a
curator has catalogued so far, not an exhaustive labelling, so a high-ranked
work missing from them may be an uncatalogued evaluation rather than an error.
A curated paper that does not appear among the citing works at all is reported
as unmatched: its DOI may differ from the one OpenAlex holds, or OpenAlex may
lack its reference list, and either way the ranking says nothing about it.

    python scripts/measure_against_cfcr.py <path to a CFCR checkout> [--names]

--names scores each model's catalogued name and aliases, as `--name` would.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from pathlib import Path

from whochecked import openalex
from whochecked.report import build_rows, sections
from whochecked.score import usable_names

MODELS = ("model:enformer", "model:alphagenome", "model:nucleotide-transformer",
          "model:borzoi", "model:evo2", "model:gears", "model:chrombpnet")


def doi_of(paper_id: str) -> str:
    return openalex.parse_query(paper_id)[1].lower()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cfcr", type=Path)
    ap.add_argument("--names", action="store_true")
    ap.add_argument("--cache-dir", type=Path, default=Path("cache"))
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    with open(args.cfcr / "db" / "entity_paper.tsv", encoding="utf-8") as f:
        links = list(csv.DictReader(f, delimiter="\t"))
    with open(args.cfcr / "db" / "entities.tsv", encoding="utf-8") as f:
        entities = {r["entity_id"]: r for r in csv.DictReader(f, delimiter="\t")}

    totals = {"ranked": [], "title_only": [], "zero": [], "unmatched": 0}
    for eid in MODELS:
        primary_id = next(r["paper_id"] for r in links
                          if r["entity_id"] == eid and r["role"] == "primary")
        curated = {doi_of(r["paper_id"]) for r in links if r["entity_id"] == eid
                   and r["role"] in ("benchmark", "critique")}
        primary, _ = openalex.resolve(primary_id)
        citing, total = openalex.cached_citing(openalex.short_id(primary),
                                               args.cache_dir)
        forms = set()
        if args.names:
            e = entities[eid]
            forms, _ = usable_names([e["name"], *json.loads(e["aliases"] or "[]")])
        s = sections(build_rows(openalex.authors(primary), citing, forms))

        found = set()
        print(f"\n{eid}: {len(curated)} curated, {len(citing)} of {total} citing works read")
        for name, rows in s.items():
            ranks = [i + 1 for i, r in enumerate(rows)
                     if (r["doi"] or "").lower().removeprefix("https://doi.org/") in curated]
            found |= {(rows[i - 1]["doi"] or "").lower() for i in ranks}
            totals[name] += [(i, len(rows)) for i in ranks]
            print(f"  {name:<10} {len(ranks):>3} curated of {len(rows):>5} rows"
                  + (f", ranks {ranks}" if ranks and name != "zero" else ""))
        unmatched = len(curated) - len(found)
        totals["unmatched"] += unmatched
        print(f"  unmatched  {unmatched:>3} curated papers not among the citing works")

    print("\nAll models:")
    for name in ("ranked", "title_only", "zero"):
        got = totals[name]
        line = f"  {name:<10} {len(got):>3} curated"
        if got and name != "zero":
            line += (f", median rank {statistics.median(i for i, _ in got):g}, "
                     f"{sum(i <= 50 for i, _ in got)} in the top 50 of their list")
        print(line)
    print(f"  unmatched  {totals['unmatched']:>3}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
