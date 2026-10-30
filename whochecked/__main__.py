"""
whochecked/__main__.py
----------------------
    python -m whochecked <DOI | arXiv id | title> [--name NAME ...] [--all]
                         [--cache-dir cache]

Prints the primary paper and every work citing it, ranked by how much each
reads like an evaluation, with each one's author overlap with the primary
paper. Needs the [walk] extra and network, and reads OPENALEX_API_KEY from the
environment.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from whochecked import openalex
from whochecked.report import build_rows, render
from whochecked.score import usable_names


def main() -> int:
    ap = argparse.ArgumentParser(prog="whochecked")
    ap.add_argument("query", nargs="+",
                    help="a DOI, an arXiv id, or a title (best guess)")
    ap.add_argument("--name", action="append", default=[],
                    help="the resource's name, scored where a citing work "
                         "writes it; repeat for aliases")
    ap.add_argument("--all", action="store_true",
                    help="also list the works that scored zero or below")
    ap.add_argument("--cache-dir", type=Path, default=Path("cache"))
    args = ap.parse_args()
    # Author names are any script. Redirected output otherwise takes the
    # locale's encoding, and GBK, for one, cannot write every name.
    sys.stdout.reconfigure(encoding="utf-8")

    if not openalex.OPENALEX_KEY:
        print("no OPENALEX_API_KEY -- running on the keyless budget, 1,000 "
              "requests a day shared across this network", file=sys.stderr)

    primary, how = openalex.resolve(" ".join(args.query))
    if primary is None:
        # Not found is a gap in OpenAlex, not a fact about the paper.
        print("OpenAlex has no work for that query. This says nothing about "
              "whether the paper exists or has been evaluated.")
        return 1

    citing, total = openalex.cached_citing(openalex.short_id(primary),
                                           args.cache_dir)
    name_forms, dropped = usable_names(args.name)
    rows = build_rows(openalex.authors(primary), citing, name_forms)
    print(render(primary, how, rows, total, name_forms, dropped, args.all))
    return 0


if __name__ == "__main__":
    sys.exit(main())
