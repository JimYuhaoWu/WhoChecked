"""
whochecked/openalex.py
----------------------
Resolve a resource's primary paper and walk the works that cite it, from
OpenAlex. Adapted from CFCR's literature/01_search.py, whose `_get`,
DOI-by-filter resolution and paged citation walk were earned there.

Two departures:

* No contact address. CFCR sends one with every request for OpenAlex's polite
  pool; an API key is required now, and a second address would be one more
  contact this repository has to document.
* The input is a stranger's, not a catalogue's. It is a DOI, an arXiv id or a
  title, and a title resolves to a best guess, which the caller is told.

Needs the [walk] extra:
    pip install -e ".[walk]"
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

OPENALEX = "https://api.openalex.org/works"
UA = "whochecked/0.0.1"

# Read from the environment and stored nowhere: a key written into the
# repository is a key in its history, and this history is public and permanent.
# Absent is a supported state for a single command-line run -- the keyless
# budget answers a few hundred calls -- so the caller warns and carries on.
OPENALEX_KEY = os.environ.get("OPENALEX_API_KEY") or None

OA_SELECT = "id,doi,title,publication_year,type,authorships"

# OpenAlex stops page-based paging at 10,000 results: 50 pages of 200.
MAX_PAGES = 50


class FetchError(RuntimeError):
    """OpenAlex gave up after the retries."""


# The longest `Retry-After` this will sit through. A per-second 429 asks for a
# few seconds and is worth waiting out; OpenAlex's daily-budget 429 sends the
# seconds until midnight UTC, and sleeping on that parks the process for hours
# having printed one line. Above the cap the wait becomes a FetchError, and
# `cached_citing` means a rerun loses nothing already fetched.
MAX_RETRY_AFTER = 60


def _get(params: dict) -> dict:
    """
    Four attempts, then give up loudly. Honours Retry-After up to
    MAX_RETRY_AFTER when the server sends one; otherwise backs off 3s, 6s, 9s.
    Never returns None: a dropped request that came back empty would read as a
    paper with no authors or no citing works, which is a claim, not a gap.
    Unlike CFCR's, the FetchError messages carry no request parameters: here
    those are someone's query.
    """
    for attempt in range(4):
        try:
            # The key goes in a header, not the query string: a query string is
            # the part of a request that gets logged.
            headers = {"User-Agent": UA}
            if OPENALEX_KEY:
                headers["Authorization"] = f"Bearer {OPENALEX_KEY}"
            r = requests.get(OPENALEX, params=params, headers=headers, timeout=60)
            if r.status_code == 429:
                wait = int(r.headers.get("Retry-After", 10))
                if wait > MAX_RETRY_AFTER:
                    raise FetchError(
                        f"rate limited for {wait}s, longer than the "
                        f"{MAX_RETRY_AFTER}s this will wait -- a quota rather "
                        f"than a burst. Nothing already fetched is lost; run "
                        f"again once it resets.")
                print(f"    rate limited, waiting {wait}s", file=sys.stderr)
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r.json()
        except FetchError:
            # Not retryable, and `except Exception` below would swallow it
            # back into the loop.
            raise
        except Exception as exc:                        # noqa: BLE001
            print(f"    retry {attempt + 1}: {exc}", file=sys.stderr)
            time.sleep(3 * (attempt + 1))
    raise FetchError("no answer from OpenAlex after 4 attempts")


def parse_query(query: str) -> tuple[str, str]:
    """
    ("doi", doi) or ("title", title).

    arXiv mints `10.48550/arXiv.<id>` for every submission and OpenAlex indexes
    it, so an arXiv id resolves exactly, as a DOI. Anything that is neither is
    taken as a title.
    """
    q = query.strip()
    q = re.sub(r"(?i)^(https?://(dx\.)?doi\.org/|doi:)", "", q)
    if re.fullmatch(r"10\.\d{4,9}/\S+", q):
        return "doi", q
    m = (re.fullmatch(r"(?i)arxiv:(\S+?)(v\d+)?", q)
         or re.fullmatch(r"(\d{4}\.\d{4,5})(v\d+)?", q))
    if m:
        return "doi", f"10.48550/arXiv.{m.group(1)}"
    return "title", q


def resolve(query: str) -> tuple[dict | None, str]:
    """
    The primary paper's OpenAlex work, and how it was found: "doi" or "title".

    A DOI is asked as a `filter` rather than as `/works/doi:<doi>`, because the
    single-entity form 404s on a DOI OpenAlex does not have, and `_get` would
    retry that four times before raising. A filter answers an absent DOI with
    an empty result set. A title is a best guess, never the paper for certain,
    so it is never used as a fallback for a DOI that did not resolve.
    """
    kind, value = parse_query(query)
    # A comma separates filters, so one inside a title would split it.
    flt = f"doi:{value}" if kind == "doi" else f"title.search:{value.replace(',', ' ')}"
    hits = _get({"filter": flt, "select": OA_SELECT, "per-page": 1}).get("results")
    return (hits[0] if hits else None), kind


def short_id(work: dict) -> str:
    return work["id"].rsplit("/", 1)[-1]


def authors(work: dict) -> list[str]:
    return [a["author"]["display_name"]
            for a in (work.get("authorships") or [])
            if (a.get("author") or {}).get("display_name")]


def citing_works(oa_id: str) -> tuple[list[dict], int]:
    """Every work citing `oa_id`, paged, and the total OpenAlex reports."""
    out, page = [], 1
    while True:
        d = _get({"filter": f"cites:{oa_id}", "per-page": 200,
                  "page": page, "select": OA_SELECT})
        out += d["results"]
        total = d["meta"]["count"]
        print(f"    page {page}: {len(out)}/{total}", file=sys.stderr)
        if len(out) >= total or not d["results"] or page >= MAX_PAGES:
            return out, total
        page += 1
        time.sleep(0.2)


def cached_citing(oa_id: str, cache_dir: Path) -> tuple[list[dict], int]:
    """
    `citing_works`, through a per-paper cache.

    Keyed on the OpenAlex id, not the date: a paper's citing set does not change
    meaningfully between two runs an hour apart, and a run that wants it fresh
    deletes the file. The cache holds what people asked about, so it stays out
    of the repository (.gitignore).
    """
    f = cache_dir / f"citing_{oa_id}.json"
    if f.exists():
        cached = json.loads(f.read_text(encoding="utf-8"))
        print(f"    cached: {len(cached['citing'])} works", file=sys.stderr)
        return cached["citing"], cached["total"]
    works, total = citing_works(oa_id)
    cache_dir.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps({"root": oa_id,
                             "fetched": datetime.now(timezone.utc).isoformat(),
                             "total": total,
                             "citing": works}, ensure_ascii=False),
                 encoding="utf-8")
    return works, total
