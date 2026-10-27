# WhoChecked

**Has anyone independent actually evaluated this resource, and may you reuse
it?** Give WhoChecked a research resource and the paper that introduced it. It
walks the citation graph, finds the papers that evaluate it, works out which of
those share authors with the original, and reports what it found.

It does not tell you whether the resource is good. It tells you who checked it,
whether they were at arm's length, and on what terms the thing can be reused —
and it shows the derivation, so you can disagree with it.

> **Status: nothing is built.** This repository currently holds the design, the
> prior-art survey that motivates it, and the risks. See
> [ROADMAP.md](ROADMAP.md).

## Why this exists

A resource's own paper reports its own evaluation. That is the weakest possible
evidence and it is the evidence almost every catalogue records. The question
that matters — *did anyone outside the authoring group check this?* — is
answerable from metadata that is already public, by comparing author lists, and
as far as a survey on 2026-10-27 could establish, **nothing does it.**

| Tool | What it does | Where it stops |
|---|---|---|
| [scite.ai](https://scite.ai/) | classifies 1.2–1.6B *citation statements* as supporting / mentioning / contrasting | about claims in prose, not about who did the evaluating; subscription |
| [CitePrism](https://arxiv.org/pdf/2605.16000) | flags "questionable self-cite" from author overlap plus low relevance | closest mechanism, opposite direction: audits a manuscript's own reference list for integrity, not a resource's validation status |
| self-citation tools ([scholar_citations](https://github.com/rahvis/scholar_citations), Self-Citations Checker) | self-citation rate for an author profile; any shared author counts | author-level bibliometrics; no notion of a resource or of an evaluation |
| [OpenEBench](https://openebench.bsc.es/tool/) (ELIXIR) | platform where communities *run* benchmarks; 34k+ tools from bio.tools | hosts benchmarks. Its own documentation describes a "neutral framework" but records no evaluator independence and computes no conflict-of-interest measure |
| [bio.tools](https://bio.tools/bio.tools) | tool metadata registry | no evaluation-independence field |
| [Curate Science](https://curatescience.org/app/replications), [ReplicationWiki](https://blog.repec.org/2020/08/04/a-replication-database-for-economics-and-social-sciences-the-replicationwiki/), FORRT Replication Database | track replications in psychology and economics | their "independence" means independent *samples*, not independent *authors*; field-specific and hand-curated |
| [ModelGo](https://dl.acm.org/doi/10.1145/3589334.3645520), DPExplorer, [REUSE](https://github.com/fsfe/reuse-tool) | ML licence-compliance analysis | licence only; repository or workflow input, not a DOI; no evidence layer |

The unoccupied combination is all five of these at once:

1. **resource-level** — not author-level bibliometrics, not claim-level citation sentiment
2. **independence derived from author overlap** between the resource's own paper and the papers that evaluate it
3. **joined to reuse terms** — the licence of the code or weights, where one can be resolved
4. **computed on user-submitted input**, not browsed from a fixed catalogue
5. **field-agnostic** — author names and citation graphs carry no discipline

## What it reports, and why it refuses to conclude

The hard question is *which citing papers are evaluations?* A lexicon can rank
candidates; it cannot classify them. That limit is measured, not assumed — it
came out of [CFCR](https://github.com/JimYuhaoWu/cell_fate_control_resources),
where a scope score retained 17 of 29 curated resources at one threshold and 9
at another, and where inclusion stayed a human decision for exactly that
reason.

WhoChecked does not pretend otherwise. It answers with a distribution, not a
verdict:

> 47 citing works. 12 score as evaluations. 9 of those share no authors with
> the primary paper. Here is each one, with its lexicon breakdown, its author
> overlap as a fraction, and what is missing.

So the judgement that cannot be automated becomes the *output* rather than a
hidden step. CFCR keeps a curator in the loop because it asserts a tier on a
card; WhoChecked asserts nothing, which is what lets it run unattended.

## Relationship to CFCR

[CFCR](https://cellfatecontrol.com) is a curated catalogue of cell-fate-control
resources whose distinguishing feature is an evidence layer: `evidence_tier`
derived from author overlap, never asserted. WhoChecked is that derivation,
turned outward — same mechanism, any field, computed on demand for input the
user supplies rather than for a catalogue someone curated.

They are deliberately separate projects. A catalogue you browse and a server
that computes on your data are different things, and the venue rules treat them
as different things.

**The shared derivation should become a library both import, not a copy in
each.** CFCR's own review discipline treats "a second home" for a shared thing
as a defect — four copies of one contact address cost it a cleanup — and this
function is the thing both projects would claim as novel. Deciding this is
[ROADMAP.md](ROADMAP.md) M1's first item.

## Licence

Not yet chosen. It has to be a standard licence shown on the landing page if
this is ever submitted as a web server, so this is a real decision rather than
a formality.
