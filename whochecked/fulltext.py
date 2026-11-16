"""
whochecked/fulltext.py
----------------------
Stage 2: read the full text of a citing work the user supplies, and show where
and how it cites the resource (docs/stage2-spec.md).

What it may and may not assert, as everywhere in WhoChecked:

* It shows the sentences, so the reader judges. The full-text score ranks the
  papers read in full among themselves; it does not classify.
* Every gap is unknown. A PDF with no text layer, a reference list that was not
  found, a citation whose marker was lost in extraction -- each is reported as
  what could not be seen, never as "does not cite".

What keeps an upload private:

* The file is never written to disk. Its bytes go to a child process on stdin,
  the child returns the text on stdout, and only the evidence drawn from that
  text is kept, in the job, and deleted with it.
* No file name is read or kept.

The child process runs this module (`python -m whochecked.fulltext`), with a
memory and a time limit, so a malformed or hostile PDF fails one upload rather
than the server.
"""

from __future__ import annotations

import io
import json
import re
import subprocess
import sys
import unicodedata

from whochecked.lexicon import (BENCH_ABSTRACT, CRIT_ABSTRACT, hits, lexicon,
                                names)

MAX_FILE = 20 * 1024 * 1024
MAX_PAGES = 100
TIMEOUT = 60                       # seconds a child may take on one file
CHILD_MEMORY = 300 * 1024 * 1024   # bytes of address space for that child
MAX_SENTENCES = 12                 # citing sentences kept per paper
MAX_SENTENCE = 600                 # characters kept per sentence

DOI = re.compile(r"\b10\.\d{4,9}/[^\s\"<>]+", re.I)
HEADING = re.compile(
    r"^\s*(?:\d{1,2}(?:\.\d{1,2})*\.?\s+)?"
    r"(abstract|introduction|background|results(?: and discussion)?|discussion|"
    r"conclusions?|methods|materials and methods|methods and materials|"
    r"online methods|star\s*★?\s*methods|experimental procedures)\s*$", re.I)
REFS = re.compile(r"^\s*(references(?: and notes)?|bibliography|literature cited|"
                  r"works cited)\s*$", re.I)
# Extraction can space out a line's characters ("1 5 . K a y a"), so a
# reference number may carry single spaces between its digits.
ENTRY = re.compile(r"^\s*\[?((?:\d ?){1,3})[\].)]\s*\S")
# Extraction sometimes drops the space after a full stop ("cells 17.Both").
SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[\"(\[]?[A-Z0-9])|(?<=[a-z0-9][.!?])(?=[A-Z][a-z ])")
NUM_GROUP = re.compile(r"[\[(]\s*(\d{1,3}(?:\s*[,–—-]\s*\d{1,3})*)\s*[\])]")
# A superscript citation loses its raise in extraction and becomes a bare number
# after a word: "requirements 15." Only looked for when a numbered paper does
# not cite in square brackets, and shown as a guess, because "chromosome 1" and
# "for 5 min" look alike.
SQUARE = re.compile(r"\[\s*\d{1,3}(?:\s*[,–—-]\s*\d{1,3})*\s*\]")
# Glued to the word ("data17 and") it may be followed by anything; after a
# space it must end a clause ("recommended 17."), so "for 5 min" is not one.
_NUMS = r"(\d{1,3}(?:\s?[,–-]\s?\d{1,3})*)"
BARE = re.compile(r"(?<=[a-z)])" + _NUMS + r"(?=[\s.,;:]|$)"
                  r"|(?<=[a-z)])\s" + _NUMS + r"(?=[.,;:]|$)")


# ------------------------------------------------------------ extraction

def _child_limits() -> None:                    # pragma: no cover - POSIX only
    import resource
    resource.setrlimit(resource.RLIMIT_AS, (CHILD_MEMORY, CHILD_MEMORY))


def extract(data: bytes) -> dict:
    """
    The pages of a PDF or a plain-text file, read in a child process.

    {"state": "read", "pages": [...], "truncated": bool}, or
    {"state": "unreadable"} when there is no text to read, or
    {"state": "failed"} when the child ran out of time or memory or crashed.
    """
    if not data.startswith(b"%PDF"):
        text = data.decode("utf-8", errors="replace")
        return ({"state": "read", "pages": [text], "truncated": False}
                if text.strip() else {"state": "unreadable"})
    try:
        out = subprocess.run(
            [sys.executable, "-m", "whochecked.fulltext"], input=data,
            capture_output=True, timeout=TIMEOUT,
            preexec_fn=_child_limits if sys.platform != "win32" else None)
    except subprocess.TimeoutExpired:
        return {"state": "failed"}
    if out.returncode != 0:
        return {"state": "failed"}
    got = json.loads(out.stdout)
    if not any(p.strip() for p in got["pages"]):
        return {"state": "unreadable"}
    return {"state": "read", **got}


def _child() -> int:                            # pragma: no cover - subprocess
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(sys.stdin.buffer.read()))
    pages = []
    for page in reader.pages[:MAX_PAGES]:
        try:
            pages.append(page.extract_text() or "")
        except Exception:                       # noqa: BLE001 - one bad page
            pages.append("")
    json.dump({"pages": pages, "truncated": len(reader.pages) > MAX_PAGES},
              sys.stdout)
    return 0


# ------------------------------------------------------------ reading

def _norm(text: str) -> str:
    """Lower-cased words only, single-spaced: what title matching compares."""
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


def _squeeze(text: str) -> str:
    """Letters and digits only. Extraction inserts and drops spaces inside
    words ("ef ficient"), so a reference entry is compared without them."""
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _clean_doi(d: str) -> str:
    return d.rstrip(".,;:)]}").lower()


def _doi_key(d: str | None) -> str | None:
    return _clean_doi(d.split("doi.org/")[-1]) if d else None


def match_row(pages: list[str], rows: list[dict]) -> tuple[dict | None, str | None, str | None]:
    """
    (row, how, doi found) for an upload: the report row it is, matched by a DOI
    on its first page, else by its title appearing there. `how` is "doi",
    "title" or None. A title match is a guess and is shown as one.
    """
    first = pages[0] if pages else ""
    found = [_clean_doi(d) for d in DOI.findall(first)]
    by_doi = {_doi_key(r.get("doi")): r for r in rows if r.get("doi")}
    hit = [by_doi[d] for d in dict.fromkeys(found) if d in by_doi]
    if len(hit) == 1:
        return hit[0], "doi", found[0] if found else None
    head = _norm(" ".join(pages[:1]))
    titled = [r for r in rows if r.get("title")
              and len(_norm(r["title"]).split()) >= 5
              and _norm(r["title"]) in head]
    if len(titled) == 1:
        return titled[0], "title", found[0] if found else None
    return None, None, found[0] if found else None


def _split(pages: list[str]) -> tuple[list[tuple[int, str, str]], list[str]]:
    """
    (body, reference lines): the body as (page, section, line) and the lines
    after the last references heading. With no heading found, the reference
    lines are empty and the body is everything.
    """
    lines = [(i + 1, ln) for i, p in enumerate(pages) for ln in p.splitlines()]
    starts = [k for k, (_, ln) in enumerate(lines) if REFS.match(ln)]
    cut = starts[-1] if starts else len(lines)
    body, section = [], None
    for page, ln in lines[:cut]:
        m = HEADING.match(ln)
        if m:
            section = m.group(1).strip().capitalize()
            continue
        body.append((page, section, ln))
    return body, [ln for _, ln in lines[cut + 1:]]


def _entries(ref_lines: list[str]) -> dict[int, str]:
    """A numbered reference list as {number: entry}, or {} if it is not one."""
    out, cur = {}, None
    for ln in ref_lines:
        m = ENTRY.match(ln)
        if m and int(m.group(1).replace(" ", "")) == (cur or 0) + 1:
            cur = int(m.group(1).replace(" ", ""))
            out[cur] = ln
        elif cur is not None:
            out[cur] += " " + ln
    return out if len(out) >= 5 else {}


def _surname(author: str) -> str | None:
    words = re.findall(r"[^\W\d_]+", author)
    return words[-1] if words else None


def find_reference(ref_lines: list[str], primary: list[dict]) -> dict:
    """
    Where the reference list holds a resource paper. {"found": False} when it
    does not appear in the extracted list, which is unknown, not absent.
    Otherwise the citation marker: {"number": n}, or for an unnumbered list
    {"surname": ..., "year": ...}.
    """
    entries = _entries(ref_lines)
    flat = " ".join(ref_lines)
    for p in primary:
        doi = _doi_key(p.get("doi"))
        words = _norm(p.get("title") or "").split()
        title = _squeeze(" ".join(words[:8])) if len(words) >= 4 else None
        def holds(text: str) -> bool:
            return bool((doi and doi in re.sub(r"\s+", "", text).lower())
                        or (title and title in _squeeze(text)))
        for n, entry in entries.items():
            if holds(entry):
                return {"found": True, "number": n, "paper": p.get("n"),
                        "entries": len(entries)}
        if not entries and holds(flat):
            first = (p.get("authors") or [None])[0]
            return {"found": True, "surname": first and _surname(first),
                    "year": p.get("year"), "paper": p.get("n")}
    return {"found": False}


def _numbers(group: str) -> set[int]:
    """The reference numbers in a group such as "3, 7-9", ranges expanded."""
    out = set()
    for part in group.split(","):
        ends = [int(x) for x in re.split(r"[–—-]", part) if x.strip()]
        if len(ends) == 2 and 0 < ends[1] - ends[0] < 50:
            out |= set(range(ends[0], ends[1] + 1))
        elif len(ends) == 1:
            out.add(ends[0])
    return out


def _sentences(body: list[tuple[int, str, str]]) -> list[dict]:
    """Sentences with the page and section each starts in. Lines are joined
    first, so a sentence broken across lines is one sentence."""
    out, run, key = [], [], None
    def flush():
        text = re.sub(r"(\w)-\s+(\w)", r"\1\2", " ".join(run))
        for s in SENTENCE_END.split(re.sub(r"\s+", " ", text).strip()):
            if s:
                out.append({"page": key[0], "section": key[1], "text": s})
    for page, section, ln in body:
        if key is not None and (page, section) != key:
            flush()
            run = []
        key = (page, section)
        run.append(ln)
    if run:
        flush()
    return out


def read(pages: list[str], primary: list[dict], name_forms: set[str]) -> dict:
    """The evidence one paper's text gives about the resource."""
    pages = [unicodedata.normalize("NFKC", p) for p in pages]   # ligatures
    body, ref_lines = _split(pages)
    ref = find_reference(ref_lines, primary)
    ref["list_found"] = bool(ref_lines)
    sents = _sentences(body)
    # Square brackets in a paper that cites by superscript hold other things
    # ("[0.5, 1]"), so the test is how many references are cited that way.
    in_square = {n for s in sents for g in SQUARE.findall(s["text"])
                 for n in _numbers(g.strip("[] "))}
    bracketed = len(in_square) >= max(5, 0.3 * ref.get("entries", 0))
    cited = []
    for i, s in enumerate(sents):
        low = s["text"].lower()
        how = None
        if ref.get("number") is not None and any(
                ref["number"] in _numbers(g) for g in NUM_GROUP.findall(s["text"])):
            how = "number"
        elif ref.get("number") is not None and not bracketed and any(
                ref["number"] in _numbers(g) for m in BARE.findall(s["text"])
                for g in m if g):
            how = "bare number"
        elif ref.get("surname") and ref.get("year") and re.search(
                re.escape(ref["surname"].lower()) + r"\W.{0,40}?" + str(ref["year"]), low):
            how = "author and year"
        elif name_forms and names(name_forms, low):
            how = "name"
        if how:
            cited.append((i, how))
    # Citations first: a sentence that cites the paper says more than one
    # that only names the resource, and only the first few are kept.
    cited.sort(key=lambda c: (c[1] == "name", c[0]))
    # Scored on the sentences that cite the paper and their neighbours, or,
    # with none found, on those naming the resource; nothing else. A paper
    # about the resource names it everywhere, so names alone would score the
    # whole paper.
    scored = [i for i, h in cited if h != "name"] or [i for i, _ in cited]
    window = " ".join(sents[j]["text"] for i in scored
                      for j in range(max(0, i - 1), min(len(sents), i + 2))).lower()
    bench, crit = lexicon("", window)
    return {"reference": ref,
            "n_cited": sum(h != "name" for _, h in cited),
            "n_named": sum(h == "name" for _, h in cited),
            "sentences": [{**{k: sents[i][k] for k in ("page", "section")},
                           "text": sents[i]["text"][:MAX_SENTENCE], "how": how}
                          for i, how in cited[:MAX_SENTENCES]],
            "scored_on": "citations" if any(h != "name" for _, h in cited)
                         else "names" if cited else None,
            "ft_score": round(bench + crit, 2),
            "ft_terms": sorted(set(hits(BENCH_ABSTRACT + CRIT_ABSTRACT, window)))}


if __name__ == "__main__":                      # pragma: no cover
    raise SystemExit(_child())
