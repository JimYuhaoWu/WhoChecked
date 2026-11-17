# Case study — who checks bioinformatics resources, and how soon

Draft plan, 2026-11-16. Nothing has been run. Decisions still open are marked
**Open** and listed at the end. The aim is one finding for the NAR proposal,
due to be sent around 20 December, and the labelled sample the ROADMAP already
asks for.

## The question

For resources of three kinds — computational models, datasets, and
sequencing assays — how many have at least one evaluation by a group
independent of the resource's authors that WhoChecked can surface, and how
long after publication did the first one appear?

This is a question about bioinformatics, answered with a field-agnostic tool,
which is what the proposal needs.

## What the tool can and cannot answer here

WhoChecked ranks; it does not classify. So it cannot by itself say whether a
resource has been evaluated. The study therefore has two parts:

1. **WhoChecked surfaces.** For each resource, it ranks the citing works.
2. **A person labels.** A reader labels the top-ranked works, and a random
   sample of the rest, as *evaluates*, *uses*, *mentions* or *unclear*, from
   the title and abstract, without seeing the score.

The finding comes from the labels. The tool's part is to make labelling a few
works per resource enough. The random sample measures what the ranking misses,
and gives the ROADMAP its missing baseline: the 188 curated rows are all
positives, so precision has never been measured.

Independence comes from the tool, as everywhere: author overlap between the
resource's paper and each work labelled *evaluates*, with the derivation kept.

## Choosing the resources

Chosen by rules written down before any resource is run, so the result cannot
be steered by the choice. Each frame was tried in OpenAlex on 2026-11-16.

- **Datasets: papers in the NAR Database Issue.** NAR's own curated frame.
  The 2018 issue (D1) has 76 papers with "database" in the title; most
  heavily cited: PRIDE (6,794), Pfam (4,910).
- **Assays: papers introducing a sequencing assay.** No curated list found.
  A title search for "-seq" in 2015–2019 returns 4,684 works, mostly
  software (StringTie, Salmon) and biology using an assay, so this frame needs
  an eligibility rule applied by a person: the paper's main contribution is a
  wet-lab protocol. Commercial assays without a paper of their own are out,
  as the ROADMAP records; those with one are in, flagged.

  *Is the frame big enough?* Tried 2026-11-17: titles with "seq" or
  "sequencing", 2016–2019, at least 300 citing works, give 458 papers. A
  first pass by title alone finds about 20 that introduce an assay (among
  them Perturb-seq, CEL-Seq2, DroNc-seq, Seq-Well, Slide-seq, scNMT-seq,
  MULTI-seq, PRO-seq, CIRCLE-seq, DART-seq, TSA-seq, PLAC-seq, END-seq,
  Omni-ATAC, nanopore direct RNA sequencing), well over the 8 needed. But a
  title search misses assays whose titles do not say "seq": CUT&RUN,
  CUT&Tag, CITE-seq ("simultaneous epitope and transcriptome measurement"),
  10x Chromium. So the frame adds a second pass, an abstract search for a
  new method in the same years, and both passes are screened by the same
  rule.
- **Models: the models catalogued by CFCR.** Settled 2026-11-17. A
  keyword search for deep learning returns protein structure, climate and
  fusion physics; CFCR's catalogue is a curated frame of sequence-to-function
  and cell-fate models with their primary papers linked. It also shows the
  two projects working together: CFCR collects, WhoChecked checks.
  - **Seven models are excluded**: Enformer, AlphaGenome, Nucleotide
    Transformer, Borzoi, Evo 2, GEARS and ChromBPNet. Their 188 curated
    evaluations are what WhoChecked's ranking was measured against, so they
    would be measured in-sample.
  - **CFCR's catalogue is mostly recent**: of 320 models, 11 are from
    2016–2019, and 4 of those have 300 citing works (Basset, Basenji,
    ExPecto, and the 5′ UTR model of 2019). In the shared window of
    **2015–2021** exactly 8 are eligible: DeepSEA, Basset, ExPecto, Basenji,
    the 5′ UTR model, Akita, DNABERT and BPNet, as of CFCR commit `0bc6afa`.
    All 8 are taken, so for models the draw rule below does not apply.
  - **CFCR is still changing, so its list is frozen.** See *Freezing the
    sample* below.
  - **The frame is one curator's**, and what CFCR chose to catalogue may
    lean towards prominent models. The write-up says so.

Within each frame:

- **Published 2015–2021, for all three kinds.** Settled 2026-11-17. Every
  resource has had at least five years to be checked; the assay pilot found
  comparisons appearing four to eight years after the assay. Resources of
  2020–2021 have had less time than those of 2015, so results are reported by
  year of publication as well as by kind.
- **At least 300 citing works.** This selects on the chance to be checked,
  never on being checked: the condition is fixed before WhoChecked is run on
  anything, and a resource with no evaluation found stays in the sample. That
  is a finding, not a failed draw. Choosing assays because they are known to
  have been compared would answer the question before asking it.
- **The 5 most cited eligible papers, and 3 drawn at random from the rest.**
  Settled 2026-11-17. The 5 lean towards resources that had the most chances
  to be checked; the 3 show whether a typical resource differs. The two are
  reported apart, never pooled, and 3 is an illustration, not an estimate.
  The random draw uses a seed written down before it is made.
  **Open 2.**
- **At most 10,000 citing works,** the tool's cap. A resource above it is
  replaced by the next, and the replacements are listed.

## Freezing the sample

CFCR is in active curation, so its model list will change while this study
runs and after. A reviewer comparing the sample with CFCR's catalogue later
must be able to tell routine curation from a choice made after seeing
results. So:

- **The sample is fixed before WhoChecked runs on any of it**, and written to
  `labels/case_study_sample.tsv`: each resource's kind, name, DOI, year, why
  it is eligible, and for models the CFCR commit it was read from. The draw's
  seed is in the same file.
- **Later CFCR changes never change the sample.** A model added to the
  catalogue afterwards is not added; one removed is not removed.
- **A correction is recorded, not made silently.** If a sampled resource
  turns out to be ineligible (a wrong DOI, a review rather than a primary
  paper), it is replaced by the next by the same rule, and the change is
  logged in the same file, as a new row whose `status` gives its date and
  reason, before its labels are
  looked at where possible.
- **The drift is checked, not assumed.** A script compares the frozen model
  list with CFCR's catalogue at a given commit and lists every 2015–2021
  model added or removed since, so the write-up can state how the catalogue
  changed and that the sample did not follow it.

## The frame and sample as drawn, 2026-11-17

Every candidate considered, and the decision made on it before anything was
run, is in `labels/case_study_frame.tsv` (1,457 rows). The sample is in
`labels/case_study_sample.tsv`, written by `scripts/case_study_draw.py`, which
writes the same file every time it runs. `scripts/cfcr_drift.py` reports how
CFCR's catalogue has moved since; at drawing it had not.

- **Models: 8 eligible, all taken.** Read from CFCR `0bc6afa`: DeepSEA,
  DNABERT, Basset, BPNet, ExPecto, Basenji, the 5′ UTR model and Akita.
- **Datasets: 43 eligible** of 338 NAR Database Issue papers of 2015–2021
  with at least 300 citing works. Eligible means the first paper of a
  resource; updates and new papers for older resources are out. Top 5:
  AlphaFold Protein Structure Database, LinkedOmics, iProX, CellMarker,
  TISCH. At random: REDIportal, CircNet, ETCM.
- **Assays: 85 eligible** of 1,094 candidates, from a title search ("seq" or
  "sequencing") and an abstract search (sequencing, with method, assay,
  protocol or technique, and "we developed", "we present" or similar). Top 5:
  CITE-seq, Omni-ATAC, Slide-seq, Perturb-seq, MiFish. At random: CEL-Seq2,
  DroNc-seq, and single-nucleus RNA-seq of post-mortem neurons.

How the assays were screened, and what that misses:

- A keyword rule set aside titles that read as software or as a study using
  an assay; the remaining 281, and the set-aside titles that still named an
  assay or a method, were screened by hand, by title.
- **Excluded on purpose:** the assay pilot's resources (ATAC-seq and CUT&Tag
  papers), since their results have been seen; and protocol papers for assays
  introduced earlier (CUT&RUN, DAP-seq, PRO-seq, inDrop, FISSEQ, SLAM-seq).
- **Missed by the searches:** some well-known assays never entered the
  candidates, among them the first CUT&RUN paper and 10x Chromium, because
  neither search matched them. They are not added afterwards; adding known
  names by hand would be choosing the sample. The write-up says so.
- **One reader screened.** The eligibility calls were made by one reader from
  titles. A second look at the 128 eligible datasets and assays, and at the
  excluded ones nearest the line, is worth having before the proposal.

## Size and labelling effort

Settled 2026-11-17: **8 resources of each kind, 24 in all.** For each one,
the **top 10** ranked works with an abstract, and **5 drawn at random** from
the rest. That makes 360 labels, 3–5 hours at 30–50 seconds each, within the
time agreed.

- **Label definitions are written first**, with examples, and frozen before
  labelling.
- **A second reader labels a fifth of them** without seeing the first reader's
  labels, and agreement is reported. **Open 3:** who.
- Labels are of public papers and go into `labels/` like the name sample. No
  query from the live site is involved.
- **Run 2026-11-17** by `scripts/case_study_run.py`, 229 OpenAlex requests;
  a second run from the cache writes the same files. Each resource was
  scored with its own name, as a user would give it (the last assay has
  none). The top 10 are the highest scores among works with an abstract,
  ties broken by OpenAlex id; the random 5 come from every other work with
  an abstract, whatever its score. Works with no abstract (60 to 1,246 per
  resource) are counted in `labels/case_study_runs.tsv` and never sampled.
  The sheet a reader labels is `labels/case_study_sheet.tsv`, in shuffled
  order with no score, rank, draw or overlap; those are in
  `labels/case_study_key.tsv`. Abstracts are read from a workbook the script
  writes to `cache/`, which is not committed. The definitions are in
  `docs/case-study-labels.md`.
- The papers labelled *evaluates* that are open access are also read through
  stage 2, as a check of the full-text reading. This is optional and not part
  of the finding.

## What is reported

Per kind of resource, never as a ranking of resources (a ranking turns into a
verdict):

- How many resources have at least one *evaluates* work by an independent
  group among those labelled, and how many have none **found**. "None found"
  is not "never evaluated": the labels cover the top 10 and a sample, and
  OpenAlex misses citations. That is stated beside the number.
- The time from the resource's paper to the first independent *evaluates*
  work found.
- Precision in the top 10, and the share of *evaluates* works in the random
  sample, which estimates what the ranking misses.
- Unknowns kept apart: works with no abstract, resources whose author lists
  are missing.

Per-resource results go in a supplement, sorted by name, each with its
derivation.

## Timeline to the proposal

| Week of | Step |
|---|---|
| 16 Nov | Settle the open decisions. Write the label definitions. Draw the sample. |
| 23 Nov | Run the 24 resources. First reader labels. |
| 30 Nov | Second reader labels the overlap. Measure agreement. |
| 7 Dec | Analyse. Draft the one-page proposal around the finding. |
| 14 Dec | Revise; send around 20 December. |

Running 24 resources costs at most 24 × 51 OpenAlex requests, well inside one
day's allowance.

## Open decisions

1. ~~The frame for models~~ — settled: CFCR's catalogue at a frozen
   commit, the seven calibration models excluded; one window, 2015–2021,
   for all three kinds.
2. ~~Most cited first, or a random draw~~ — settled: the top 5 and 3 at
   random, for datasets and assays.
3. **The second reader**, to be settled after talking in person on
   2026-11-17. Someone other than the project's author makes the agreement
   figure independent.
4. ~~The size~~ — settled: 8 of each kind, 10 + 5 labels each.
