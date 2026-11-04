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

* At most JOBS_PER_HOUR jobs are accepted an hour, counted across everyone
  from the jobs on disk. A limit per visitor would need their address, and
  the server keeps nothing about who submitted.
* A job starts only when OpenAlex's reported daily budget can pay for the
  costliest query; until then it waits in the queue instead of failing.
"""

from __future__ import annotations

import argparse
import math
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

from flask import Flask, abort, redirect, render_template, request, url_for

from whochecked import jobs, openalex
from whochecked.report import (GAP_RULE, MATCHING_RULE, SCORING_RULE, VERDICTS,
                               build_rows, overlap_counts, sections)
from whochecked.score import MIN_NAME, usable_names

# Longer than any DOI or title; a cap on what one form can make the worker do.
MAX_QUERY = 500

# Jobs accepted an hour, from everyone together. A cold walk costs a few
# requests and at most 51, so 30 an hour stays well inside a 10,000-a-day key
# for ordinary papers; the budget check covers the rest.
JOBS_PER_HOUR = 30
LIMIT_WINDOW = timedelta(hours=1)

# Public papers, so trying the tool needs nothing of the visitor's own.
EXAMPLES = [{"label": "ChromBPNet, a deep-learning model of chromatin "
                      "accessibility (2024 preprint)",
             "query": "10.1101/2024.12.25.630221", "names": "ChromBPNet"}]


def run(cache_dir: Path):
    """The walk a job runs, returning what its page renders."""
    def go(query: str, names: list[str]) -> dict:
        try:
            primary, how = openalex.resolve(query)
            if primary is None:
                return {"found": False, "how": how}
            citing, total = openalex.cached_citing(openalex.short_id(primary),
                                                   cache_dir)
        except openalex.FetchError as exc:
            # FetchError's messages name no query, so they are safe to show.
            raise jobs.FailedJob(str(exc)) from None
        forms, dropped = usable_names(names)
        return {"found": True, "how": how, "total": total,
                "primary": {"id": openalex.short_id(primary),
                            "title": primary.get("title"),
                            "year": primary.get("publication_year"),
                            "doi": primary.get("doi"),
                            "authors": openalex.authors(primary)},
                "name_forms": sorted(forms), "dropped": dropped,
                "rows": build_rows(openalex.authors(primary), citing, forms)}
    return go


def create_app(store: jobs.Store) -> Flask:
    app = Flask(__name__)

    @app.context_processor
    def retention():
        return {"retention_days": jobs.RETENTION.days,
                "jobs_per_hour": JOBS_PER_HOUR}

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
        query = request.form.get("query", "").strip()
        names = [n.strip() for n in request.form.get("names", "").split(",")
                 if n.strip()]
        if not query or len(query) > MAX_QUERY:
            return render_template(
                "index.html", examples=EXAMPLES, max_query=MAX_QUERY,
                problem=("Enter a DOI, an arXiv id or a title." if not query
                         else f"That is longer than {MAX_QUERY} characters.")
            ), 400
        now = datetime.now(timezone.utc)
        recent = store.submitted_since(now - LIMIT_WINDOW)
        if len(recent) >= JOBS_PER_HOUR:
            # A place frees when the oldest job still counted turns an hour old.
            wait = recent[len(recent) - JOBS_PER_HOUR] + LIMIT_WINDOW - now
            minutes = max(1, math.ceil(wait.total_seconds() / 60))
            resp = app.make_response((render_template(
                "index.html", examples=EXAMPLES, max_query=MAX_QUERY,
                problem=(f"WhoChecked has taken its {JOBS_PER_HOUR} checks for "
                         f"this hour, from everyone together. Try again in "
                         f"{minutes} minute{'s' if minutes != 1 else ''}.")), 429))
            resp.headers["Retry-After"] = str(minutes * 60)
            return resp
        # 303: the browser fetches the job page with GET, so a reload of it
        # does not resubmit.
        return redirect(url_for("job", job_id=store.submit(query, names)), 303)

    @app.get("/r/<job_id>")
    def job(job_id):
        j = store.get(job_id)
        if j is None:
            abort(404)
        ctx = {"job": j}
        if j["state"] == "queued":
            ctx["ahead"] = store.position(job_id)
            if not openalex.budget_allows():
                ctx["resumes"] = openalex.budget_resets.strftime("%H:%M UTC")
        r = j.get("result")
        if r and r["found"]:
            ctx.update(r=r, s=sections(r["rows"]), verdicts=VERDICTS,
                       counts=overlap_counts(r["rows"]),
                       gap_rule=GAP_RULE, scoring_rule=SCORING_RULE,
                       matching_rule=MATCHING_RULE, min_name=MIN_NAME)
        return render_template("job.html", **ctx)

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
                     kwargs={"ready": openalex.budget_allows},
                     daemon=True).start()
    from waitress import serve
    serve(create_app(store), host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
