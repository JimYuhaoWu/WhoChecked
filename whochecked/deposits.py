"""
whochecked/deposits.py
----------------------
The licence declared where a resource's weights are deposited: a Hugging Face
model or a Zenodo record, from a link the user gives. Nothing here guesses the
deposit from the paper.

One request a job, without a token. Hugging Face allows 500 per five minutes
and Zenodo 30 a minute, and the server accepts at most 30 papers an hour.

Both licences are what the uploader declared, in a metadata field. Unlike
GitHub's detection nothing has read a licence file, so a report says "declares".

Absence is not evidence. No licence declared, a record not found and a failed
request are each reported as what they are, and none of them is a statement
about whether the weights may be reused.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

import requests

from whochecked.openalex import UA

_WWW = r"(?:https?://)?(?:www\.)?"
_REST = r"(?:[/?#].*)?"

HF_LINK = re.compile(_WWW + r"huggingface\.co/([A-Za-z0-9_.-]{1,96})/"
                     r"([A-Za-z0-9_.-]{1,96})" + _REST, re.IGNORECASE)
ZENODO_LINK = re.compile(
    r"(?:" + _WWW + r"zenodo\.org/records?/"
    r"|(?:https?://(?:dx\.)?doi\.org/|doi:|" + _WWW + r"zenodo\.org/doi/)?"
    r"10\.5281/zenodo\.)(\d{1,12})" + _REST, re.IGNORECASE)

# The first part of a huggingface.co path that is not an owner of models.
NOT_MODELS = {"datasets", "spaces", "docs", "blog", "papers", "posts", "models",
              "collections", "organizations", "settings", "tasks", "learn"}


def parse_link(text: str) -> str | None:
    """A deposit's link, cleaned, or None if it is not one this can read."""
    m = HF_LINK.fullmatch(text)
    if m is not None:
        if m[1].lower() in NOT_MODELS or m[1] in (".", "..") or m[2] in (".", ".."):
            return None
        return f"huggingface.co/{m[1]}/{m[2]}"
    m = ZENODO_LINK.fullmatch(text)
    return f"zenodo.org/records/{m[1]}" if m is not None else None


def _fetch(url: str, gone: tuple[int, ...], answer: dict) -> tuple[dict | None, dict]:
    """The reply's JSON, or None and the answer that says why there is none."""
    try:
        r = requests.get(url, timeout=30, headers={"User-Agent": UA})
        if r.status_code in gone:
            return None, answer | {"state": "not_found"}
        if r.status_code != 200:
            return None, answer | {"state": "no_answer"}
        return r.json(), answer
    except (requests.RequestException, ValueError):
        return None, answer | {"state": "no_answer"}


def _huggingface(answer: dict, model: str) -> dict:
    # A model that does not exist, or a private one, is a 401, not a 404.
    data, answer = _fetch(f"https://huggingface.co/api/models/{model}",
                          (401, 404), answer)
    if data is None:
        return answer
    # An old short name is answered under the model's current name.
    if data.get("id"):
        answer |= {"ref": data["id"], "url": f"https://huggingface.co/{data['id']}"}
    if data.get("gated"):
        answer["gated"] = data["gated"]
    card = data.get("cardData") or {}
    declared = card.get("license")
    if isinstance(declared, list):
        declared = ", ".join(str(x) for x in declared)
    if not declared:
        return answer | {"state": "none"}
    if declared == "other":
        return answer | {"state": "custom", "licence": card.get("license_name")}
    return answer | {"state": "declared", "licence": str(declared)}


def _zenodo(answer: dict, record: str) -> dict:
    data, answer = _fetch(f"https://zenodo.org/api/records/{record}",
                          (404, 410), answer)
    if data is None:
        return answer
    # A concept id is answered by the latest version, under that version's id.
    if data.get("id"):
        answer |= {"ref": f"zenodo.{data['id']}",
                   "url": f"https://zenodo.org/records/{data['id']}"}
    meta = data.get("metadata") or {}
    if meta.get("access_right") not in (None, "open"):
        answer |= {"access": meta["access_right"], "embargo": meta.get("embargo_date")}
    declared = (meta.get("license") or {}).get("id")
    if not declared:
        return answer | {"state": "none"}
    return answer | {"state": "declared", "licence": declared}


def licence(link: str) -> dict:
    """
    What the deposit at a `parse_link` link declares today. `state` is one of:

    declared   a licence: `licence` says which, as the service writes it
    custom     Hugging Face's "other": `licence` is its given name, if any
    none       no licence declared
    not_found  no such record, or a private one
    no_answer  the request failed or was refused

    `gated` (Hugging Face) and `access`, `embargo` (Zenodo) are added when the
    files cannot simply be downloaded.
    """
    host, ref = link.split("/", 1)
    answer = {"checked": datetime.now(timezone.utc).date().isoformat(),
              "url": f"https://{link}"}
    if host == "huggingface.co":
        return _huggingface(answer | {"host": "Hugging Face", "ref": ref,
                                      "source": "Hugging Face model card"}, ref)
    record = ref.rsplit("/", 1)[1]
    return _zenodo(answer | {"host": "Zenodo", "ref": f"zenodo.{record}",
                             "source": "Zenodo record"}, record)
