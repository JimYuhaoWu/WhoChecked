# Case study — label definitions

Draft, 2026-11-17. To be frozen before the first label is written; a change
after that is recorded here with its date and the items it touches.

Each item on `labels/case_study_sheet.tsv` is a work that cites one of the 24
resources. Read its title and abstract and give it **one** label for what it
does **with that resource**, not for what kind of paper it is. A reader does not
see its score, its rank, whether it was drawn at random, or its author overlap
with the resource's paper; `labels/case_study_key.tsv` holds those and is not
opened until both readers are done.

## The labels

**evaluates** — the work measures how well the resource does what it claims,
and reports the result. Its abstract says, or makes plain, that the resource
is one of the things measured.

- A benchmark that runs the resource against others on shared data.
- A comparison of an assay with another assay on the same samples.
- A study of where the resource fails: errors, bias, poor reproducibility,
  missing coverage, wrong annotations.
- A new method that reports beating the resource on a stated measure, when
  the resource is named as a baseline.

**uses** — the work relies on the resource to get its own results, without
measuring the resource.

- Running the model to score variants; taking markers from the database;
  profiling samples with the assay.
- Building on the resource (a new model on its architecture, a database
  importing its records) without reporting how well it does.

**mentions** — the work cites the resource without using or measuring it, or
the abstract gives no sign of either.

- Reviews, perspectives, and introductions that list it among others.
- A paper whose abstract is about something else entirely.

**unclear** — the abstract cannot tell evaluates, uses and mentions apart for
this resource. Write why in `note`.

## Rules for the hard cases

1. **The abstract decides, not the reader's knowledge.** A paper the reader
   knows to be a benchmark, whose abstract does not say so, is *unclear*, with
   the knowledge written in `note`. The finding is about what the tool can
   surface from what OpenAlex holds.
2. **A benchmark of many** counts as *evaluates* only if the abstract names
   this resource, or names its class so that this resource must be in it
   ("all published single-cell protocols"; "deep learning models of chromatin
   accessibility" is not enough on its own). Otherwise *unclear*.
3. **Beating a baseline** is *evaluates* when the resource is named as the
   thing beaten. "Outperforms existing methods" with no names is *unclear*.
4. **Using and measuring.** When a work does both, *evaluates* wins only if
   the measurement is reported as a result, not as a check in passing ("we
   confirmed DeepSEA's predictions with a reporter assay for three variants"
   is *uses*).
5. **An update or a protocol of the same resource**, by its own authors, that
   reports how well the resource does is still *evaluates*. Who wrote it is
   not the label's business: independence comes from author overlap, which
   the tool derives afterwards.
6. **Not in English, or no abstract on the sheet** — *unclear*, noted. The
   sheet should hold none without an abstract; report any.
7. **One label.** If torn between two, take the one the abstract supports
   more plainly and write the other in `note`.

## What the labels are used for

The finding counts *evaluates* works and the time from each resource's paper
to the first one by an independent group, per kind of resource, never as a
ranking of resources. Precision in the top 10 and the share of *evaluates*
among the random 5 measure the ranking. Every number keeps *unclear* apart:
an item that could not be labelled is unknown, not a no.
