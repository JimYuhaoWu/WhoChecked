"""
scripts/name_sample.py
----------------------
A hand-labelled sample of author-name matches, and the error rate it measures.

The whole output is a name comparison, so its error rate is the tool's
correctness ceiling (ROADMAP M2). This draws name pairs from the citing works
of CFCR's seven models, for a person to label, and then counts the labels.

A pair is a primary-paper author and a citing-work author, unique per model,
in one of three strata:

  strong   same key, and weak_match finds nothing against it
  weak     same key, and weak_match names a reason
  near     different keys, but one name is the other written surname-first,
           or the same surname with one side's first forename among the other
           side's middle names -- the two ways the key misses a person, which
           a sample of matches alone can never find

The weak and near strata are the rare ones, so each stratum is sampled
separately and the rates are reported per stratum. The overall false-match rate
reweights strong and weak by how many pairs each holds, so oversampling the
weak ones does not inflate it.

    python scripts/name_sample.py sample <CFCR checkout> labels.tsv [--n 60]
    python scripts/name_sample.py score labels.tsv

Label each row in the `label` column: same, different, or unsure. Unsure rows
are counted and left out of the rates.
"""

from __future__ import annotations

import argparse
import csv
import random
import sys
from pathlib import Path

from measure_against_cfcr import MODELS
from whochecked import openalex
from whochecked.overlap import _tokens, norm_author, weak_match

STRATA = ("strong", "weak", "near")
COLUMNS = ("stratum", "stratum_pairs", "model", "primary_name", "citing_name",
           "reasons", "occurrences", "primary_work", "example_work", "label")


def near(p: str, a: str) -> bool:
    tp, ta = _tokens(p), _tokens(a)
    if not tp or not ta or norm_author(p) == norm_author(a):
        return False
    if ta[0] == tp[-1] and ta[-1][0] == tp[0][0] or        tp[0] == ta[-1] and tp[-1][0] == ta[0][0]:
        return True
    return tp[-1] == ta[-1] and (
        ta[0][0] in {t[0] for t in tp[1:-1]}
        or tp[0][0] in {t[0] for t in ta[1:-1]})


def pairs(cfcr: Path, cache_dir: Path) -> dict[str, list[dict]]:
    with open(cfcr / "db" / "entity_paper.tsv", encoding="utf-8") as f:
        links = list(csv.DictReader(f, delimiter="\t"))
    found = {}
    for eid in MODELS:
        primary_id = next(r["paper_id"] for r in links
                          if r["entity_id"] == eid and r["role"] == "primary")
        primary, _ = openalex.resolve(primary_id)
        citing, _ = openalex.cached_citing(openalex.short_id(primary), cache_dir)
        p_names = set(openalex.authors(primary))
        for w in citing:
            for a in set(openalex.authors(w)):
                for p in p_names:
                    if norm_author(p) == norm_author(a) and norm_author(a):
                        reasons = weak_match(p, a)
                        stratum = "weak" if reasons else "strong"
                    elif near(p, a):
                        reasons, stratum = [], "near"
                    else:
                        continue
                    key = (eid, p, a)
                    if key not in found:
                        found[key] = {"stratum": stratum, "model": eid,
                                      "primary_name": p, "citing_name": a,
                                      "reasons": ", ".join(reasons),
                                      "occurrences": 0,
                                      "primary_work": primary["id"],
                                      "example_work": w["id"], "label": ""}
                    found[key]["occurrences"] += 1
    by = {s: [] for s in STRATA}
    for row in found.values():
        by[row["stratum"]].append(row)
    return by


def sample(args) -> int:
    by = pairs(args.cfcr, args.cache_dir)
    rng = random.Random(args.seed)
    out = []
    for s in STRATA:
        rows = sorted(by[s], key=lambda r: (r["model"], r["primary_name"],
                                            r["citing_name"]))
        for r in rng.sample(rows, min(args.n, len(rows))):
            out.append({**r, "stratum_pairs": len(rows)})
        print(f"{s:<7} {len(rows):>6} pairs, {min(args.n, len(rows))} sampled")
    # Shuffled, so the labeller does not see which stratum a row came from.
    rng.shuffle(out)
    with open(args.out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, COLUMNS, delimiter="\t", lineterminator="\n")
        w.writeheader()
        w.writerows(out)
    print(f"wrote {len(out)} rows to {args.out}")
    return 0


def score(args) -> int:
    with open(args.labels, encoding="utf-8") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    bad = {r["label"] for r in rows} - {"same", "different", "unsure", ""}
    if bad:
        print(f"labels must be same, different or unsure, not {sorted(bad)}")
        return 1
    rates, sizes = {}, {}
    for s in STRATA:
        got = [r for r in rows if r["stratum"] == s]
        if not got:
            continue
        sizes[s] = int(got[0]["stratum_pairs"])
        n = {k: sum(r["label"] == k for r in got)
             for k in ("same", "different", "unsure", "")}
        decided = n["same"] + n["different"]
        # A match is wrong when the people differ; a near miss is wrong when
        # they are the same person.
        wrong = n["different"] if s != "near" else n["same"]
        what = "false matches" if s != "near" else "missed matches"
        line = (f"{s:<7} {len(got)} of {sizes[s]} pairs sampled: same {n['same']}, "
                f"different {n['different']}, unsure {n['unsure']}, "
                f"unlabelled {n['']}")
        if decided:
            rates[s] = wrong / decided
            line += f"; {what} {wrong}/{decided} = {rates[s]:.1%}"
        print(line)
    if "strong" in rates and "weak" in rates:
        total = sizes["strong"] + sizes["weak"]
        overall = (rates["strong"] * sizes["strong"]
                   + rates["weak"] * sizes["weak"]) / total
        print(f"false matches among all {total} matched pairs, reweighted by "
              f"stratum: {overall:.1%}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("sample")
    a.add_argument("cfcr", type=Path)
    a.add_argument("out", type=Path)
    a.add_argument("--n", type=int, default=60, help="pairs per stratum")
    a.add_argument("--seed", type=int, default=1)
    a.add_argument("--cache-dir", type=Path, default=Path("cache"))
    b = sub.add_parser("score")
    b.add_argument("labels", type=Path)
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    return sample(args) if args.cmd == "sample" else score(args)


if __name__ == "__main__":
    sys.exit(main())
