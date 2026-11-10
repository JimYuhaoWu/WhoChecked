"""
scripts/make_sample.py
----------------------
Rebuild whochecked/sample.json, the frozen report behind /sample, by running
the site's example against the live services. Everything in it is public: the
example's own paper, and the works that cite it.

    python scripts/make_sample.py

Reads the OpenAlex key from the environment, as the server does.
"""

import json
import tempfile
from pathlib import Path

from whochecked import deposits, github, web


def main() -> int:
    ex = web.EXAMPLES[0]
    # A fresh cache, so the sample's date is the day it was made.
    with tempfile.TemporaryDirectory() as d:
        result = web.run(Path(d))(ex["query"], [ex["names"]],
                                  github.parse_repo(ex["repo"]),
                                  deposits.parse_link(ex["weights"]))
    web.SAMPLE.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n",
                          encoding="utf-8", newline="\n")
    print(f"{web.SAMPLE}: {len(result['rows'])} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
