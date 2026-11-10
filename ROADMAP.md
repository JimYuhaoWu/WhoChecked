# WhoChecked roadmap

Milestones are defined by **exit criteria, not dates**, for the same reason
CFCR's are: the dominant cost here is unmeasured, and a date on it would be
invented. The only dates in this file are imposed from outside.

Origin: a strategy discussion on 2026-10-27, recorded in CFCR's ROADMAP.md
under "A second venue, considered and declined for CFCR itself". The idea
started as a field-agnostic resource collector — users pick keywords and get
their own catalogue — and that form is barred from the venue it was aimed at,
for reasons in **The venue** below. What survived the constraint is the half
that was always the novel one: the derivation, not the collection.

---

## M0 — design and prior art ✅ done

- [x] Prior-art survey establishing that nothing computes evaluator
      independence for a resource — the table in [README.md](README.md)
- [x] The reframe that makes it automatable: report the distribution, do not
      conclude
- [x] Venue eligibility checked against the live submission rules
- [x] Name chosen, repository created

**What it cost to learn:** the original "one-click resource website" idea fails
two explicit exclusions rather than needing a better pitch. See **The venue**.

## M1 — the derivation, as a library ✅ done

The smallest thing that is useful and testable, with no server attached.

- [x] **Decide where the derivation lives** — WhoChecked owns it, as the
      importable module `whochecked.overlap`, and CFCR imports it rather than
      keeping a copy. It came from CFCR's `scripts/schema.py`: `norm_author`,
      `classify_overlap` and `PARTIAL_MAX`. `derive_tier` stays in CFCR,
      because a tier is CFCR's assertion and WhoChecked asserts nothing.
      One behaviour changed on the way: an empty author list on either side
      now classifies as `unknown`. CFCR's copy returned `independent`, and
      guarded against that at its call sites instead
- [x] Switch CFCR to import `whochecked.overlap`, and delete its copy — CFCR
      `b7b9c2c`, pinned at `603778d`; CFCR `fc2ad6a` moved the pin to
      `2fd9509`, past the fix that drops empty normalized names (`9806597`),
      and no tier moved
- [x] Resolve a resource's primary paper from a DOI, an arXiv id, or a title
- [x] Walk its citing works
- [x] Score each citing work as a candidate evaluation, and **show the
      breakdown** rather than only the total — `whochecked.score`, on
      `whochecked.lexicon`. WhoChecked owns the lexicon, as it owns the overlap
      derivation; CFCR's genomics terms and catalogue signals stay in CFCR
- [x] Switch CFCR's triage to import `whochecked.lexicon`, and delete its copy
      — CFCR `2979ece`
- [x] Classify author overlap between primary and each candidate, as a
      fraction, with the matching rule stated
- [x] Emit a report: candidates ranked, overlap per candidate, and an explicit
      statement of what is missing

**Exit:** given a DOI on the command line, the tool prints a report a
researcher can act on, and every number in it can be traced to the metadata it
came from.

**Measured on 2026-10-30** against the 188 `benchmark`/`critique` rows CFCR's
curators accepted for seven models, with
`scripts/measure_against_cfcr.py`. That is recall-at-rank only: the rows are
not an exhaustive labelling, so precision is not measurable against them.

| | curated found | median rank | in the top 50 |
|---|---|---|---|
| OpenAlex's own order, unscored | 186 | 255.5 | 10 |
| scored, ranked section | 175 | 56 | 81 |
| scored with the model's name (`--names`) | 175 | 34 | 112 |
| title-only section, either way | 6 | 2 to 2.5 | 6 |

Five score zero, and two are not among the citing works at all: both are
DART-Eval, whose OpenAlex record has no reference list (M2's second risk).

**Reusable from CFCR** rather than written fresh: the OpenAlex resolve-and-walk
(`literature/01_search.py`), the benchmark/critique lexicon
(`literature/triage_rules.py`), the reference-list gate that replaced name
matching, and licence detection through the GitHub API
(`literature/07_enrich.py`).

## M2 — the four risks, measured

Each of these is a way the tool is wrong without the user being able to tell,
which is worse than being unavailable. They are ordered by how badly they bite.

- [x] **Author-name disambiguation.** This is the correctness ceiling: the
      entire output is a name comparison. CFCR has already been burned twice —
      every two-letter surname (He, Li, Xu, Wu) collapsed to `anon` under a
      longest-token rule, and Europe PMC writes "He B" where Crossref writes
      "Bowen He", so the surname sits at opposite ends depending on the source.
      The self-citation literature names variants and homonyms as its main
      error source. **Exit: a measured error rate on a hand-labelled sample,
      and uncertainty shown in the output wherever a match is weak.**
  - [x] Weak matches shown: `whochecked.overlap.weak_match` marks a shared
        author matched on an initial alone, on a surname of two letters or
        fewer, or with differing forenames or middle initials. It flags and
        never reclassifies
  - [x] Error rate, labelled on 2026-11-02 — `scripts/name_sample.py` drew
        every matched pair (51 strong, 11 weak) and 12 near misses from the
        seven models' walks, in `labels/name_sample.tsv`. Per unique pair,
        with 95% Wilson intervals:

        | | different people | interval |
        |---|---|---|
        | strong matches | 0 of 51 | 0 to 7.0% |
        | weak matches | 8 of 10, 1 unsure | 49 to 94% |
        | all matches | 8 of 61 | 6.8 to 23.8% |
        | near misses that were one person | 0 of 12 | 0 to 24% |

        Every false match is a weak one, so the flag carries the risk, and
        every one errs toward less independence. The labels found one reason
        the flag did not then name, different middle initials ("A. B. Lund"
        against "Ana C. Lund", an invented pair); it names it now, and no
        strong pair moved, so the rate stands
- [x] **The citation graph is systematically incomplete.** DART-Eval's OpenAlex
      record carries `referenced_works_count: 1`, so it appears in no `cites:`
      result for anything it benchmarks. Conference proceedings are the hole,
      and machine-learning venues are both where it is worst and where a likely
      user base lives. **Exit: coverage measured per venue type, and the gap
      disclosed in every report rather than silently absorbed.**
  - [x] Measured on 2026-11-02 with `scripts/reference_gaps.py`: the share of
        2020-2025 articles, preprints and reviews OpenAlex holds no reference
        list for, by venue type.

        | venue type | all works | cited 5+ times |
        |---|---|---|
        | journal | 34.2% of 34.0M | 2.7% of 11.0M |
        | repository (preprints) | 82.2% of 4.9M | 44.3% of 177k |
        | conference | 52.8% of 24k | 14.9% of 3.9k |
        | no venue recorded | 85.5% of 1.4M | 53.3% of 34k |

        This measures missing reference lists, not missing evaluations: no
        list of evaluations exists to count against. The two populations
        bracket it, the first padded with works that really cite nothing, the
        second leaning old. OpenAlex files only 24k works under conference
        venues, so most machine-learning proceedings sit under repository,
        where the hole is widest
  - [x] Disclosed: every report quotes these rates, as a dated snapshot in
        `whochecked.report` rather than a live count, which would add twelve
        requests to every query
- [x] **OpenAlex now requires an API key.** Keyless access is 1,000 requests a
      day shared across a whole network IP, which a public server exhausts
      immediately. **Exit: a key, a measured per-query request budget, and a
      cache, since a paper's citing set does not change hour to hour.**
  - [x] Budget measured on 2026-11-02, the seven models from an empty cache:
        one request to resolve plus one per 200 citing works, 2 to 8 per
        model and 28 for all seven, and 1 once cached. The ceiling is 51, at
        the 10,000-result paging limit, so the keyless 1,000 a day is about
        20 worst-case queries
  - [x] Cache — `cached_citing`, per paper, outside the repository
  - [x] A key, used live on 2026-11-03: the seven models from an empty cache
        took the same 2 to 8 requests each, and OpenAlex reported a daily
        limit of 10,000 against the keyless 1,000. That is about 196
        worst-case queries a day, or about 2,500 at these seven's mean of 4.
        The key appears in no output, cache or log, and a key OpenAlex rejects
        now fails at once instead of being retried as an outage
- [x] **Latency.** A citation walk is never instant, and the venue requires a
      bookmarkable results link whenever results are not immediate.
      **Exit: jobs survive a page reload.**
  - [x] Measured on 2026-11-03, with the key, the seven models from an empty
        cache: 4.6 to 26.5 s, about 3 s per page of 200 citing works; 1.7 to
        3.8 s once cached, which is the resolve request and start-up. The
        51-request ceiling would be about two and a half minutes. Not
        immediate, so jobs are needed
  - [x] Jobs, designed here and built with the server in M3, retention 7
        days. A reload, a closed tab and a server restart all lose nothing:
    * **A job** is one query, its state (queued, running, done, failed) and
      its report, kept on disk, so a reload, a closed tab or a server restart
      loses nothing; a job queued when the server stops runs when it starts.
    * **Its link** is a random id, `secrets.token_urlsafe(16)`, never derived
      from the query: a hash of a DOI would let anyone holding that DOI test
      whether someone had asked about it.
    * **The query travels in a POST body**, never a query string, so it is in
      no URL, no access log and no referrer. It is stored only inside its
      job, with no address, no account and no cookie beside it.
    * **The results page sends `Referrer-Policy: no-referrer`.** Its links
      out (every DOI) would otherwise hand the job's URL, and with it the
      report, to each publisher.
    * **Retention is fixed and stated** on the help page, and a job is
      deleted when it expires. The length is an M3 decision.
    * **The citing cache is shared** across jobs, keyed by OpenAlex id: it
      holds what was asked about but never who asked, and it is never listed
      or served. Since 2026-11-04 it is deleted on the jobs' schedule, 7 days
      after a walk was fetched, so it outlives no job that asked.
    * **One worker** sends every OpenAlex request, so the daily budget and
      the per-second limit are spent in one place.

## M3 — the server

Built on 2026-11-03 as `whochecked.web` (Flask, served by waitress) and
`whochecked.jobs`. Installed on 2026-11-04 on an AWS Lightsail instance in
Singapore ($7 a month, 1 GB), as a systemd service listening on localhost
only; not yet public.

    pip install -e ".[server]"
    python -m whochecked.web --port 8000

- [x] Compute on user-submitted input: a DOI, several DOIs, or a resource and
      its paper — a DOI, arXiv id or title a line, up to 5 papers of one
      resource, with the resource's names optional. They make one report: a
      work citing two is one row, overlap is against all of their authors,
      and with any paper's authors unknown no work is called independent.
      Each paper counts against the hourly limit
- [x] Rich output — the ranked evidence with its derivation, not a verdict:
      every row shows its score's parts, the words that matched, its overlap
      fraction and which shared authors are weak
- [x] Sample data to try without supplying anything — one example, ChromBPNet
- [x] Help pages explaining how to read a report, including what it cannot say,
      linking to sample output — `/sample`, the example's report frozen by
      `scripts/make_sample.py` so its link does not expire
- [x] HTTPS on 443 — https://whochecked.org, with Caddy in front and a
      Let's Encrypt certificate it renews itself
- [x] Licence on the landing page
- [x] No login, no registration, no email; cookie consent for anything
      persistent, no third-party or tracking cookies — the server sets no
      cookie at all, so there is nothing to consent to
- [x] User-submitted input kept private — built to the job design under M2
      and tested: the query is in no URL, no cookie and nothing logged by the
      server. Verified on the deployed host on 2026-11-10 with a test query:
      it reached no log and no URL, and the proxy keeps no access log at all,
      because a job's link is the only key to someone's query
- [x] Bookmarkable results link — `/r/<random id>`, kept 7 days
- [x] Rate limit, announced on the landing and help pages: at most 30 papers
      an hour across everyone, counted from the jobs on disk, so no visitor's
      address is ever held. A job waits in the queue, rather than failing,
      while OpenAlex's reported daily budget (`X-RateLimit-Remaining`) cannot
      pay for the costliest query

**Exit:** a stranger pastes a DOI and learns something they could not have got
from the resource's own paper.

## M4 — citable release and the server paper

- [ ] Archival DOI
- [ ] CITATION.cff
- [ ] A co-maintainer
- [ ] One-page proposal to the editor
- [ ] Manuscript

## After M4 — reading full papers

Not scheduled, and nothing is built. A title and an abstract can rank candidates
but cannot show whether *this* resource was among the things evaluated. The
full text can: where the citation sits, whether the resource is in a comparison
table, whether metrics are reported beside it.

- [ ] A labelled sample of citing works (evaluates, uses, mentions), to measure
      precision on titles and abstracts. The 188 curated rows are all positives,
      so there is no baseline yet, and "full text is better" stays a hypothesis
      until it is measured against one
- [ ] Full text as a second source of evidence: open-access text where it can be
      fetched, and key papers a user uploads. A paper without full text stays
      unknown, never "only mentions"
- [ ] The report shows the sentences that cite the resource, so the reader
      judges. A score from them still ranks; it does not classify
- [ ] Decide how uploads are handled before building them: an upload can be a
      manuscript under embargo, so it is at least as sensitive as a query, and
      a publisher's PDF has terms of its own

---

## The venue

Target: the **Nucleic Acids Research Web Server Issue**. Verified from
<https://academic.oup.com/nar/pages/submission_webserver> and the 24th-issue
editorial <https://academic.oup.com/nar/article/54/W1/W1/8725496> on
2026-10-27.

**The gate is open**, unlike the Database Issue's invitation-only cycle:

| When | What |
|---|---|
| any time, from November 2026 | one-page summary (PDF) to the editor for suitability |
| 2 months after the approval email | manuscript due |
| ~1 May | acceptance cut-off for that year's issue |

Fixed deadlines were abolished in the 2026 editorial; proposals are taken
year-round and accepted papers appear online and in PubMed on acceptance rather
than waiting for the issue. A rejected proposal may be resubmitted after six
months. The summary must state inputs, outputs, the processing method, PubMed
IDs of prior publications, 2–4 keywords, and authors — and longer proposals are
not read.

**Three exclusions decided this project's shape.** They are why WhoChecked
computes rather than collects:

- **"Aggregators or assemblers of existing third-party tools"** are not
  eligible. A catalogue of other people's resources is one.
- **"Query-only data resources"** belong in the Database Issue.
- The server **must let users analyse their own data**. "Mere portals for
  static data, and classifiers without rich output" are excluded.

WhoChecked passes all three by construction: it derives a result from input the
user supplies, and it assembles nothing.

**Two further rules worth knowing now rather than at submission:**

- **Similar tools need a two-year interval** after any previous publication,
  anywhere. This is why WhoChecked is a separate tool rather than a mode of
  CFCR: CFCR aiming at the January 2028 Database Issue would otherwise block a
  CFCR-shaped server until 2030.
- A standard licence must be shown on the landing page. Free non-commercial
  access is now sufficient; free commercial access is no longer required.

**Already satisfiable:** no login, HTTPS, field-agnostic rather than tied to one
disease or species, and a method that may be unpublished — the 2026 editorial
allows that explicitly.

## What has to be true, and is not yet

- **A co-maintainer.** Not a nicety: the same journal states elsewhere that
  retirement or graduation of developers is not a valid reason to terminate a
  resource. CFCR does not have one either, and a second project doubles that
  gap rather than sharing it. This is the honest argument against starting here
  at all, and it is recorded rather than resolved.
- **An answer on the shared derivation**, M1's first item.
- **A measured name-matching error rate.** Without it the central claim is
  unquantified, and the central claim is the paper.
