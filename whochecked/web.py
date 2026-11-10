"""
whochecked/web.py
-----------------
The server, M3. A query is submitted by POST, becomes a job, and the job's
page is the bookmarkable link: it refreshes itself until the report is ready.

    python -m whochecked.web [--port 8000] [--jobs jobs] [--cache-dir cache]

Needs the [server] extra, and reads OPENALEX_API_KEY from the environment.

What keeps a query private, from ROADMAP's job design:

* It travels in a POST body, so it is in no URL, no access log and no
  referrer. The job's link is a random id (whochecked.jobs).
* No cookie is set, and nothing is kept about who submitted.
* Every response sends `Referrer-Policy: no-referrer`, so following a DOI
  out of a report does not hand the report's link to the publisher.

What keeps one visitor, or another site's form, from spending everyone's
OpenAlex budget:

* At most PAPERS_PER_HOUR papers are accepted an hour, counted across
  everyone from the jobs on disk. A limit per visitor would need their
  address, and the server keeps nothing about who submitted.
* A job starts only when OpenAlex's reported daily budget can pay for the
  costliest query; until then it waits in the queue instead of failing.
"""

from __future__ import annotations

import argparse
import json
import math
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

from flask import Flask, abort, redirect, render_template, request, url_for

from whochecked import deposits, github, jobs, openalex
from whochecked.report import (GAP_RULE, MATCHING_RULE, SCORING_RULE, VERDICTS,
                               build_rows, overlap_counts, sections)
from whochecked.score import MIN_NAME, usable_names

# Longer than any DOI or title; a cap on what one form can make the worker do.
MAX_QUERY = 500

# Papers of one resource in a job: a preprint and its journal version, say.
MAX_PAPERS = 5

# Papers accepted an hour, from everyone together. A cold walk costs a few
# requests and at most 51, so 30 an hour stays well inside a 10,000-a-day key
# for ordinary papers; the budget check covers the rest.
PAPERS_PER_HOUR = 30
LIMIT_WINDOW = timedelta(hours=1)

# Public papers, so trying the tool needs nothing of the visitor's own.
EXAMPLES = [{"label": "ChromBPNet, a deep-learning model of chromatin "
                      "accessibility (2024 preprint)",
             "query": "10.1101/2024.12.25.630221", "names": "ChromBPNet",
             "repo": "https://github.com/kundajelab/chrombpnet",
             "weights": "https://zenodo.org/records/7443683"}]

# The example's report, frozen by scripts/make_sample.py: a job's link expires,
# and the help pages need sample output that does not.
SAMPLE = Path(__file__).with_name("sample.json")


def budget_ready() -> bool:
    """Whether OpenAlex's reported budget can pay for the costliest job."""
    return openalex.budget_allows(MAX_PAPERS * openalex.MAX_QUERY_REQUESTS)


def run(cache_dir: Path):
    """
    The walk a job runs, returning what its page renders. Each line of the
    query is a paper of one resource, and they make one report: a work citing
    two of them is one row, and overlap is against all of their authors.
    """
    def go(query: str, names: list[str], repo: str | None = None,
           weights: str | None = None) -> dict:
        papers, works, cites = [], {}, {}
        try:
            for q in query.splitlines():
                primary, how = openalex.resolve(q)
                if primary is None:
                    papers.append({"n": len(papers) + 1, "found": False,
                                   "how": how, "query": q})
                    continue
                oa_id = openalex.short_id(primary)
                if any(p.get("id") == oa_id for p in papers):
                    continue                     # two inputs, one work
                citing, total, fetched = openalex.cached_citing(oa_id, cache_dir)
                n = len(papers) + 1
                papers.append({"n": n, "found": True, "how": how, "id": oa_id,
                               "title": primary.get("title"),
                               "year": primary.get("publication_year"),
                               "doi": primary.get("doi"),
                               "authors": openalex.authors(primary),
                               "total": total, "read": len(citing),
                               "fetched": fetched[:10]})
                for w in citing:
                    works[openalex.short_id(w)] = w
                    cites.setdefault(openalex.short_id(w), []).append(n)
        except openalex.FetchError as exc:
            # FetchError's messages name no query, so they are safe to show.
            raise jobs.FailedJob(str(exc)) from None
        found = [p for p in papers if p["found"]]
        if not found:
            return {"found": False,
                    "how": papers[0]["how"] if len(papers) == 1 else None}
        # A version citing another version is not an evaluation of the resource.
        ids = {p["id"] for p in found}
        citing = [w for i, w in works.items() if i not in ids]
        forms, dropped = usable_names(names)
        rows = build_rows([a for p in found for a in p["authors"]], citing, forms)
        # Sharing nobody with the known authors says nothing about the unknown
        # ones, so with any paper's authors missing, no work is independent.
        incomplete = len(found) < len(papers) or not all(p["authors"] for p in found)
        for row in rows:
            row["cites"] = cites[row["id"]]
            if incomplete and row["verdict"] == "independent":
                row["verdict"] = "unknown"
        return {"found": True, "papers": papers, "name_forms": sorted(forms),
                "dropped": dropped, "rows": rows,
                "repo": github.licence(repo) if repo else None,
                "weights": deposits.licence(weights) if weights else None,
                "n_found": len(found), "authors_incomplete": incomplete,
                "n_between": len(ids & set(works))}
    return go


def report_context(r: dict) -> dict:
    """What job.html needs to render a found result."""
    return {"r": r, "s": sections(r["rows"]), "verdicts": VERDICTS,
            "counts": overlap_counts(r["rows"]), "gap_rule": GAP_RULE,
            "scoring_rule": SCORING_RULE, "matching_rule": MATCHING_RULE,
            "min_name": MIN_NAME}


def create_app(store: jobs.Store) -> Flask:
    app = Flask(__name__)

    @app.context_processor
    def retention():
        return {"retention_days": jobs.RETENTION.days,
                "papers_per_hour": PAPERS_PER_HOUR,
                "max_papers": MAX_PAPERS}

    @app.after_request
    def headers(resp):
        resp.headers["Referrer-Policy"] = "no-referrer"
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["Content-Security-Policy"] = (
            "default-src 'none'; style-src 'self'; form-action 'self'; "
            "base-uri 'none'; frame-ancestors 'none'")
        # A job page is someone's query; no shared cache may keep it.
        resp.headers["Cache-Control"] = "no-store"
        return resp

    @app.get("/")
    def index():
        return render_template("index.html", examples=EXAMPLES,
                               max_query=MAX_QUERY)

    @app.post("/jobs")
    def submit():
        # One paper a line, never a comma: a title can hold a comma.
        lines = list(dict.fromkeys(ln.strip() for ln
                                   in request.form.get("query", "").splitlines()
                                   if ln.strip()))
        names = [n.strip() for n in request.form.get("names", "").split(",")
                 if n.strip()]
        link = request.form.get("repo", "").strip()
        repo = github.parse_repo(link) if link else None
        deposit = request.form.get("weights", "").strip()
        weights = deposits.parse_link(deposit) if deposit else None
        problem = ("Enter a DOI, an arXiv id or a title." if not lines
                   else f"Enter at most {MAX_PAPERS} papers, one a line."
                   if len(lines) > MAX_PAPERS
                   else f"A line is longer than {MAX_QUERY} characters."
                   if any(len(ln) > MAX_QUERY for ln in lines)
                   else "The code repository must be a github.com link, such "
                        "as https://github.com/owner/name."
                   if link and repo is None
                   else "Model weights must be a huggingface.co model link, or "
                        "a Zenodo link or DOI."
                   if deposit and weights is None else None)
        if problem:
            return render_template("index.html", examples=EXAMPLES,
                                   max_query=MAX_QUERY, problem=problem), 400
        now = datetime.now(timezone.utc)
        recent = store.submitted_since(now - LIMIT_WINDOW)
        if len(recent) + len(lines) > PAPERS_PER_HOUR:
            # Enough places are free once this paper turns an hour old.
            wait = recent[len(recent) + len(lines) - PAPERS_PER_HOUR - 1] \
                + LIMIT_WINDOW - now
            minutes = max(1, math.ceil(wait.total_seconds() / 60))
            resp = app.make_response((render_template(
                "index.html", examples=EXAMPLES, max_query=MAX_QUERY,
                problem=(f"WhoChecked takes {PAPERS_PER_HOUR} papers an hour, "
                         f"from everyone together, and this would go over. "
                         f"Try again in {minutes} "
                         f"minute{'s' if minutes != 1 else ''}.")), 429))
            resp.headers["Retry-After"] = str(minutes * 60)
            return resp
        # 303: the browser fetches the job page with GET, so a reload of it
        # does not resubmit.
        return redirect(url_for("job", job_id=store.submit("\n".join(lines), names,
                                                           repo, weights)), 303)

    @app.get("/r/<job_id>")
    def job(job_id):
        j = store.get(job_id)
        if j is None:
            abort(404)
        ctx = {"job": j}
        if j["state"] == "queued":
            ctx["ahead"] = store.position(job_id)
            if not budget_ready():
                ctx["resumes"] = openalex.budget_resets.strftime("%H:%M UTC")
        r = j.get("result")
        if r and r["found"]:
            ctx.update(report_context(r))
        return render_template("job.html", **ctx)

    @app.get("/sample")
    def sample():
        r = json.loads(SAMPLE.read_text(encoding="utf-8"))
        return render_template("job.html", job={"state": "done", "result": r},
                               sample=True, **report_context(r))

    @app.get("/help")
    def help_page():
        return render_template("help.html", gap_rule=GAP_RULE, scoring_rule=SCORING_RULE,
                               matching_rule=MATCHING_RULE)

    @app.errorhandler(404)
    def not_found(_):
        return render_template("404.html"), 404

    return app


def main() -> int:
    ap = argparse.ArgumentParser(prog="whochecked.web")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--jobs", type=Path, default=Path("jobs"))
    ap.add_argument("--cache-dir", type=Path, default=Path("cache"))
    args = ap.parse_args()
    if not openalex.OPENALEX_KEY:
        print("no OPENALEX_API_KEY -- running on the keyless budget")

    store = jobs.Store(args.jobs, cache_dir=args.cache_dir)
    stop = threading.Event()
    threading.Thread(target=jobs.work, args=(store, run(args.cache_dir), stop),
                     kwargs={"ready": budget_ready},
                     daemon=True).start()
    from waitress import serve
    serve(create_app(store), host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
