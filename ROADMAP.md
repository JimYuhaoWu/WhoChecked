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

## M1 — the derivation, as a library

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
      `b7b9c2c`. It pins `603778d`, which predates the fix that drops empty
      normalized names (`9806597`), so CFCR's pin needs bumping
- [x] Resolve a resource's primary paper from a DOI, an arXiv id, or a title
- [x] Walk its citing works
- [ ] Score each citing work as a candidate evaluation, and **show the
      breakdown** rather than only the total
- [x] Classify author overlap between primary and each candidate, as a
      fraction, with the matching rule stated
- [ ] Emit a report: candidates ranked, overlap per candidate, and an explicit
      statement of what is missing

**Exit:** given a DOI on the command line, the tool prints a report a
researcher can act on, and every number in it can be traced to the metadata it
came from.

**Reusable from CFCR** rather than written fresh: the OpenAlex resolve-and-walk
(`literature/01_search.py`), the benchmark/critique lexicon
(`literature/triage_rules.py`), the reference-list gate that replaced name
matching, and licence detection through the GitHub API
(`literature/07_enrich.py`).

## M2 — the four risks, measured

Each of these is a way the tool is wrong without the user being able to tell,
which is worse than being unavailable. They are ordered by how badly they bite.

- [ ] **Author-name disambiguation.** This is the correctness ceiling: the
      entire output is a name comparison. CFCR has already been burned twice —
      every two-letter surname (He, Li, Xu, Wu) collapsed to `anon` under a
      longest-token rule, and Europe PMC writes "He B" where Crossref writes
      "Bowen He", so the surname sits at opposite ends depending on the source.
      The self-citation literature names variants and homonyms as its main
      error source. **Exit: a measured error rate on a hand-labelled sample,
      and uncertainty shown in the output wherever a match is weak.**
- [ ] **The citation graph is systematically incomplete.** DART-Eval's OpenAlex
      record carries `referenced_works_count: 1`, so it appears in no `cites:`
      result for anything it benchmarks. Conference proceedings are the hole,
      and machine-learning venues are both where it is worst and where a likely
      user base lives. **Exit: coverage measured per venue type, and the gap
      disclosed in every report rather than silently absorbed.**
- [ ] **OpenAlex now requires an API key.** Keyless access is 1,000 requests a
      day shared across a whole network IP, which a public server exhausts
      immediately. **Exit: a key, a measured per-query request budget, and a
      cache, since a paper's citing set does not change hour to hour.**
- [ ] **Latency.** A citation walk is never instant, and the venue requires a
      bookmarkable results link whenever results are not immediate.
      **Exit: jobs survive a page reload.**

## M3 — the server

- [ ] Compute on user-submitted input: a DOI, several DOIs, or a resource and
      its paper
- [ ] Rich output — the ranked evidence with its derivation, not a verdict
- [ ] Sample data to try without supplying anything
- [ ] Help pages explaining how to read a report, including what it cannot say
- [ ] HTTPS on 443, licence on the landing page
- [ ] No login, no registration, no email; cookie consent for anything
      persistent, no third-party or tracking cookies
- [ ] User-submitted input kept private
- [ ] Bookmarkable results link

**Exit:** a stranger pastes a DOI and learns something they could not have got
from the resource's own paper.

## M4 — citable release and the server paper

- [ ] Archival DOI
- [ ] CITATION.cff
- [ ] A co-maintainer
- [ ] One-page proposal to the editor
- [ ] Manuscript

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
