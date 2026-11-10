"""
scripts/make_sample.py
----------------------
Rebuild the frozen reports behind /sample and /sample/dataset by running the
site's examples against the live services. Everything in them is public: each
example's own paper, and the works that cite it.

    python scripts/make_sample.py [model] [dataset]

With no argument, rebuilds both. Reads the OpenAlex key from the environment,
as the server does.
"""

import json
import sys
import tempfile
from pathlib import Path

from whochecked import deposits, github, web


def main() -> int:
    for ex in web.EXAMPLES:
        if sys.argv[1:] and ex["kind"] not in sys.argv[1:]:
            continue
        # A fresh cache, so the sample's date is the day it was made.
        with tempfile.TemporaryDirectory() as d:
            result = web.run(Path(d))(ex["query"], [ex["names"]],
                                      github.parse_repo(ex["repo"]),
                                      deposits.parse_link(ex["weights"]))
        ex["file"].write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n",
                              encoding="utf-8", newline="\n")
        print(f"{ex['file'].name}: {len(result['rows'])} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
