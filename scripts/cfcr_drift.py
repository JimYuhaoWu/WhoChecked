"""
scripts/cfcr_drift.py
---------------------
How CFCR's catalogue has changed since the case study's model frame was read
from it (docs/case-study-plan.md, "Freezing the sample").

The frame holds every CFCR model of 2015-2021 as it stood at the commit named
in labels/case_study_sample.tsv. CFCR is still being curated, so models will
be added, removed and re-dated. This lists each such change for 2015-2021, and
says whether it touches a sampled model. It changes nothing: the sample does
not follow the catalogue, and this is how the write-up shows that it did not.

    python scripts/cfcr_drift.py <path to a CFCR checkout>
"""

from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

FRAME = Path("labels/case_study_frame.tsv")
SAMPLE = Path("labels/case_study_sample.tsv")
YEARS = range(2015, 2022)


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    cfcr = Path(sys.argv[1])
    sys.stdout.reconfigure(encoding="utf-8")
    with FRAME.open(encoding="utf-8") as f:
        then = {r["source"].removeprefix("CFCR "): r for r in csv.DictReader(f, delimiter="\t")
                if r["kind"] == "model"}
    with SAMPLE.open(encoding="utf-8") as f:
        sampled = {r["source"].split(" @ ")[0].removeprefix("CFCR ")
                   for r in csv.DictReader(f, delimiter="\t") if r["kind"] == "model"}
    with (cfcr / "db" / "entities.tsv").open(encoding="utf-8") as f:
        now = {e["entity_id"]: e for e in csv.DictReader(f, delimiter="\t")
               if e["entity_id"].startswith("model:")
               and e["year"].isdigit() and int(e["year"]) in YEARS}
    head = subprocess.run(["git", "-C", str(cfcr), "log", "-1", "--format=%h %cs"],
                          capture_output=True, text=True).stdout.strip()

    print(f"CFCR now at {head}; frame read at the commit named in {SAMPLE}.")
    added = sorted(set(now) - set(then))
    gone = sorted(set(then) - set(now))
    redated = sorted(e for e in set(now) & set(then) if str(then[e]["year"]) != now[e]["year"]
                     and then[e]["decision"] == "eligible")
    for label, ids in (("added since, not in the frame", added),
                       ("in the frame, no longer 2015-2021 in CFCR", gone)):
        print(f"\n{len(ids)} {label}:")
        for e in ids:
            print(f"  {e}{'  <- SAMPLED' if e in sampled else ''}")
    print(f"\n{len(redated)} eligible in the frame with a different year in CFCR now:")
    for e in redated:
        print(f"  {e}: {then[e]['year']} -> {now[e]['year']}{'  <- SAMPLED' if e in sampled else ''}")
    touched = [e for e in gone + redated if e in sampled]
    print(f"\nSampled models touched by these changes: {len(touched)}. "
          "The sample stays as drawn either way.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
