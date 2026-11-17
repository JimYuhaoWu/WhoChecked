"""
scripts/case_study_run.py
-------------------------
Run WhoChecked on the case study's frozen sample and write the labelling sheet
(docs/case-study-plan.md, "Size and labelling effort").

For each resource in labels/case_study_sample.tsv this ranks every citing work
as the tool does, then takes the 10 top-ranked works that have an abstract and
5 drawn at random from the other works with an abstract. Works with no
abstract cannot be labelled from one; they are counted, never sampled.

    python scripts/case_study_run.py

Writes:
  labels/case_study_runs.tsv   per resource: what OpenAlex returned, counted
  labels/case_study_sheet.tsv  what a reader labels: no score, rank, draw or
                               author overlap, in shuffled order
  labels/case_study_key.tsv    each sheet item's draw, rank, score and overlap,
                               not to be opened until labelling is done
  cache/case_study_reading.xlsx  the sheet with abstracts, for reading. In
                               cache/ because abstracts are the publishers' to
                               publish, not this repository's; run again to
                               rebuild it.

Needs OPENALEX_API_KEY and the [walk] extra. Citing sets go through cache/, so
a second run is offline and writes the same files; a run on a fresh cache
reads OpenAlex as it is that day, and the runs file records when.
"""

from __future__ import annotations

import csv
import random
import sys
from pathlib import Path

from whochecked import openalex
from whochecked.report import build_rows
from whochecked.score import usable_names

SAMPLE = Path("labels/case_study_sample.tsv")
RUNS = Path("labels/case_study_runs.tsv")
SHEET = Path("labels/case_study_sheet.tsv")
KEY = Path("labels/case_study_key.tsv")
READING = Path("cache/case_study_reading.xlsx")
CACHE = Path("cache")
TOP, RANDOM = 10, 5
SEED = 20261117

# Each resource's own name, given to the scorer as a user would give it. The
# last assay names nothing of its own, so it is run without one.
NAMES = {"W2198606573": ["DeepSEA"], "W3127238141": ["DNABERT"],
         "W2345512687": ["Basset"], "W3130819465": ["BPNet"],
         "W2883945062": ["ExPecto"], "W2952239877": ["Basenji"],
         "W2955231772": ["Optimus 5-Prime"], "W3092624702": ["Akita"],
         "W3211795435": ["AlphaFold DB", "AlphaFold Protein Structure Database"],
         "W2767377392": ["LinkedOmics"], "W2910730299": ["iProX"],
         "W2895456557": ["CellMarker"], "W3103119004": ["TISCH"],
         "W2510286488": ["REDIportal"], "W2174483798": ["CircNet"],
         "W2898468989": ["ETCM"],
         "W2739492614": ["CITE-seq"], "W2750416916": ["Omni-ATAC"],
         "W2915848182": ["Slide-seq"], "W2561754210": ["Perturb-seq"],
         "W2254267781": ["MiFish"], "W2342688693": ["CEL-Seq2"],
         "W2747841296": ["DroNc-seq"], "W2279350325": []}


def pick(rows: list[dict], resource: str) -> list[tuple[dict, str, int | None]]:
    """(row, draw, rank) for the top 10 and the random 5. Ties in score are
    broken by OpenAlex id, so the cut at 10 does not depend on fetch order."""
    with_abs = [r for r in rows if r["has_abstract"]]
    ranked = sorted((r for r in with_abs if r["score"] > 0),
                    key=lambda r: (-r["score"], r["id"]))
    top = ranked[:TOP]
    taken = {r["id"] for r in top}
    rest = sorted((r for r in with_abs if r["id"] not in taken), key=lambda r: r["id"])
    rng = random.Random(f"{SEED}-{resource}")
    sampled = rng.sample(rest, min(RANDOM, len(rest)))
    return ([(r, "top", i + 1) for i, r in enumerate(top)]
            + [(r, "random", None) for r in sampled])


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    with SAMPLE.open(encoding="utf-8") as f:
        sample = [r for r in csv.DictReader(f, delimiter="\t")
                  if r["status"].startswith("sampled")]
    runs, sheet, key, reading = [], [], [], []
    for n, s in enumerate(sample, 1):
        primary, _ = openalex.resolve(s["doi"])
        if primary is None or openalex.short_id(primary) != s["openalex"]:
            raise SystemExit(f"{s['doi']} no longer resolves to {s['openalex']}")
        citing, total, fetched = openalex.cached_citing(s["openalex"], CACHE)
        forms, dropped = usable_names(NAMES[s["openalex"]])
        assert not dropped, dropped
        rows = build_rows(openalex.authors(primary), citing, forms)
        by_id = {openalex.short_id(w): w for w in citing}
        with_abs = sum(r["has_abstract"] for r in rows)
        runs.append({"resource": f"R{n:02d}", "kind": s["kind"], "openalex": s["openalex"],
                     "title": s["title"], "names": "; ".join(sorted(forms)),
                     "fetched": fetched[:10], "total_in_openalex": total,
                     "citing_fetched": len(rows), "with_abstract": with_abs,
                     "scored_above_zero_with_abstract":
                         sum(r["has_abstract"] and r["score"] > 0 for r in rows),
                     "no_abstract": len(rows) - with_abs,
                     "primary_authors": len(openalex.authors(primary)),
                     "overlap_unknown": sum(r["verdict"] == "unknown" for r in rows)})
        picked = pick(rows, s["openalex"])
        order = list(range(len(picked)))
        random.Random(f"{SEED}-order-{s['openalex']}").shuffle(order)
        for pos, i in enumerate(order, 1):
            r, draw, rank = picked[i]
            item = f"R{n:02d}-{pos:02d}"
            common = {"item": item, "resource": s["title"], "work": r["id"],
                      "doi": r["doi"] or "", "year": r["year"] or "", "title": r["title"] or ""}
            sheet.append({**common, "label": "", "note": ""})
            key.append({"item": item, "work": r["id"], "draw": draw, "rank": rank or "",
                        "score": r["score"], "terms": "; ".join(r["terms"]),
                        "overlap": r["verdict"], "n_shared": r["n_shared"],
                        "shared": "; ".join(r["shared"]),
                        "weak": "; ".join(f"{a} ({', '.join(v)})" for a, v in r["weak"].items())})
            reading.append({**common, "abstract": openalex.flatten_abstract(by_id[r["id"]]),
                            "label": "", "note": ""})
        print(f"R{n:02d} {s['kind']:8} {len(rows):>5} citing, {with_abs:>5} with abstract, "
              f"{len(picked)} picked  {s['title'][:50]}")

    for path, rows in ((RUNS, runs), (SHEET, sheet), (KEY, key)):
        with path.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]), delimiter="\t", lineterminator="\n")
            w.writeheader()
            w.writerows(rows)

    from openpyxl import Workbook
    from openpyxl.styles import Alignment
    wb = Workbook()
    ws = wb.active
    ws.title = "label"
    cols = list(reading[0])
    ws.append(cols)
    for r in reading:
        ws.append([r[c] for c in cols])
    for c, width in zip("ABCDEFGHI", (9, 30, 13, 20, 6, 45, 90, 11, 30)):
        ws.column_dimensions[c].width = width
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
    ws.freeze_panes = "A2"
    wb.save(READING)
    print(f"{len(sheet)} items; OpenAlex requests: {openalex.requests_sent}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
