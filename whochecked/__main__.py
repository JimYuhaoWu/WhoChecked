"""
whochecked/__main__.py
----------------------
    python -m whochecked <DOI | arXiv id | title> [--cache-dir cache]

Prints the primary paper, every work citing it, and each one's author overlap
with the primary paper. Needs the [walk] extra and network, and reads
OPENALEX_API_KEY from the environment.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from whochecked import openalex
from whochecked.report import overlap_rows, render


def main() -> int:
    ap = argparse.ArgumentParser(prog="whochecked")
    ap.add_argument("query", nargs="+",
                    help="a DOI, an arXiv id, or a title (best guess)")
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
    print(render(primary, how, overlap_rows(openalex.authors(primary), citing),
                 total))
    return 0


if __name__ == "__main__":
    sys.exit(main())
