"""
scripts/case_study_draw.py
--------------------------
Draw the case study's sample from its frame (docs/case-study-plan.md).

labels/case_study_frame.tsv holds every candidate considered, with the
decision made on it before anything was run. This takes, for each kind, every
eligible model (the frame holds exactly eight), or for datasets and assays the
5 most cited eligible papers and 3 more drawn at random from the rest, and
writes labels/case_study_sample.tsv. Run twice, it writes the same file.

    python scripts/case_study_draw.py

The sample is frozen once written: a later change to the frame, or to CFCR's
catalogue, never changes it. A sampled resource found ineligible is replaced
by hand, as a new row whose `status` says what it replaces and why, so the
file is also the record of every change (scripts/cfcr_drift.py checks CFCR).
"""

from __future__ import annotations

import csv
import random
from pathlib import Path

FRAME = Path("labels/case_study_frame.tsv")
SAMPLE = Path("labels/case_study_sample.tsv")
SEED = 20261117          # the date the sample was drawn, written down first
TOP, RANDOM, PER_KIND = 5, 3, 8
CFCR_COMMIT = "0bc6afa"  # CFCR's catalogue as read for the model frame


def draw(frame: list[dict]) -> list[dict]:
    out = []
    for kind in ("model", "dataset", "assay"):
        eligible = sorted((r for r in frame if r["kind"] == kind and r["decision"] == "eligible"),
                          key=lambda r: (-int(r["cited_by"]), r["openalex"]))
        if len(eligible) <= PER_KIND:
            picked = [(r, "all eligible") for r in eligible]
        else:
            rest = sorted(eligible[TOP:], key=lambda r: r["openalex"])
            rng = random.Random(f"{SEED}-{kind}")
            picked = ([(r, f"top {TOP} by citing works") for r in eligible[:TOP]]
                      + [(r, f"random {RANDOM}, seed {SEED}-{kind}")
                         for r in rng.sample(rest, RANDOM)])
        for r, how in picked:
            out.append({"kind": kind, "draw": how, "openalex": r["openalex"], "doi": r["doi"],
                        "year": r["year"], "cited_by_at_draw": r["cited_by"], "title": r["title"],
                        "source": r["source"] + (f" @ CFCR {CFCR_COMMIT}" if kind == "model" else ""),
                        "status": "sampled 2026-11-17"})
    return out


def main() -> int:
    with FRAME.open(encoding="utf-8") as f:
        frame = list(csv.DictReader(f, delimiter="\t"))
    rows = draw(frame)
    with SAMPLE.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), delimiter="\t", lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    for r in rows:
        print(f"{r['kind']:8} {r['draw'][:10]:10} {r['cited_by_at_draw']:>6} {r['title'][:70]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
