"""
whochecked/github.py
--------------------
The licence GitHub detects in a repository the user names, for a report's
reuse terms. The repository is the user's claim about where the resource's
code is; nothing here guesses it from the paper.

One request a job, without a token: GitHub allows 60 an hour from one address,
and the server accepts at most 30 papers an hour.

Absence is not evidence. No licence detected, a 404 and a failed request are
each reported as what they are, and none of them is a statement about whether
the code may be reused.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

import requests

from whochecked.openalex import UA

API = "https://api.github.com/repos"

# Only github.com, and only these characters reach the request's URL. Anything
# after the repository's name, such as /tree/main, is dropped.
LINK = re.compile(r"(?:https?://)?(?:www\.)?github\.com/"
                  r"([A-Za-z0-9_-]{1,39})/([A-Za-z0-9._-]{1,100}?)"
                  r"(?:\.git)?(?:[/?#].*)?", re.IGNORECASE)


def parse_repo(text: str) -> str | None:
    """`owner/name` from a github.com link, or None if it is not one."""
    m = LINK.fullmatch(text)
    if m is None or m[2] in (".", ".."):
        return None
    return f"{m[1]}/{m[2]}"


def licence(repo: str) -> dict:
    """
    What GitHub says about `owner/name` today. `state` is one of:

    licence       a licence it identified: `spdx` and `name` say which
    unidentified  a licence file it could not identify
    none          no licence detected
    not_found     no such repository, or a private one
    no_answer     the request failed or was refused
    """
    answer = {"repo": repo, "url": f"https://github.com/{repo}",
              "checked": datetime.now(timezone.utc).date().isoformat()}
    try:
        r = requests.get(f"{API}/{repo}", timeout=30,
                         headers={"User-Agent": UA,
                                  "Accept": "application/vnd.github+json"})
        if r.status_code == 404:
            return answer | {"state": "not_found"}
        if r.status_code != 200:
            return answer | {"state": "no_answer"}
        data = r.json()
    except (requests.RequestException, ValueError):
        return answer | {"state": "no_answer"}
    # A renamed repository redirects, so this can differ from what was asked.
    answer["url"] = data.get("html_url") or answer["url"]
    found = data.get("license")
    if found is None:
        return answer | {"state": "none"}
    if found.get("spdx_id") in (None, "NOASSERTION"):
        return answer | {"state": "unidentified"}
    return answer | {"state": "licence", "spdx": found["spdx_id"],
                     "name": found.get("name")}
