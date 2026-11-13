# Stage 2 — reading the papers a user supplies

Agreed 2026-11-13; drafted 2026-11-12. Nothing here is built. The four
decisions that were open are settled as proposed and listed at the end.

## What it is for

Stage 1 ranks a resource's citing works from titles and abstracts. That can say
a work reads like an evaluation; it cannot say whether *this* resource was among
the things evaluated, and it cannot tell using a dataset from checking one.
Stage 2 lets a user supply the full text of citing works they already have, and
shows, for each, where and how the resource is cited, so the reader can judge.

WhoChecked does not retrieve papers. Paywalls and publisher terms are the
user's side of the line.

## The flow

1. The user runs a stage 1 check as today: a DOI in, a report out.
2. On the finished report, the user uploads one or more papers.
3. Each upload is matched to a row of the report, or listed as a supplied paper
   OpenAlex does not record as citing the resource.
4. The row gains a full-text section: the sentences that cite the resource,
   where in the paper they sit, and a full-text score beside the abstract score.

A supplied paper outside OpenAlex's citing set is still read. This is the one
place stage 2 can partly answer the commercial-assay limit recorded in the
ROADMAP: a check that never cites the assay's paper can be supplied by hand,
and is marked as supplied rather than found.

**Decision 1 — attached to a job, not standalone.** Settled as above.
The alternative is a separate form taking a resource DOI and a folder of
papers with no citation walk. The attached form covers that case through
unmatched uploads, and keeps one report per resource.

## Input

- **PDF and plain text.** PDF is what users have. Text extracted from a PDF
  is imperfect; a scanned PDF with no text layer yields nothing and is shown
  as unreadable, never as "does not cite".
- **Limits.** The server has 909 MB of memory, about 525 MB of it free with
  the app running, two cores and 1 GB of swap. So: up to 10 files an upload
  but at most 50 MB in one request, 20 MB and 100 pages a file, 50 papers a
  job. Files are extracted one at a time, never side by side.
- **Extraction runs in a child process with a 300 MB memory limit and a
  60-second time limit**, so a malformed or hostile PDF fails one upload
  rather than the worker or the server.

**Decision 2 — `pypdf` for extraction** (pure Python, BSD, no service to run). GROBID gives section and reference structure that would
make steps 2–3 below far more reliable, but it is a Java service that would
need more memory than the current server has. PyMuPDF is excluded: AGPL.

## What is read from each paper

1. **Which row it is.** A DOI found on the first pages, matched against the
   report's rows; failing that, the title. How it was matched is shown, and a
   title match is marked as a guess, as stage 1 marks a title-resolved paper.
2. **The reference entry for the resource's paper**, found in the reference
   list by DOI, else by title words with first author and year. From it, the
   citation marker: a number such as `[12]`, or an author-year form.
3. **The sentences that cite the resource**: those carrying the marker
   (including ranges such as `[10–15]`), and those naming the resource by any
   name the user gave. Each is shown with its page and, where a heading can be
   recognised, its section (Methods, Results, …). How each sentence was found —
   marker or name — is shown.
4. **A full-text score** from the existing evaluation words, counted only in
   those sentences and their neighbours. It ranks rows that have full text
   among themselves, beside the abstract score. It does not classify.

Not in the first version: tables, figures, supplementary files, OCR.

## What absence means here

Every gap is *unknown*, never a finding:

- no text layer, or extraction failed → "could not be read";
- no reference entry found → "reference not found in the extracted text";
- an entry but no citing sentence found → "cited, but no citing sentence
  found"; superscript markers are often lost in PDF extraction;
- a row with no upload keeps its stage 1 reading, never "only mentions".

## Privacy and storage

An upload can be a manuscript under embargo, so it is treated at least as
strictly as a query:

- **Sent in a POST body**, never in a URL.
- **The file is never written to disk.** It is read in memory, the text is
  extracted, and the file is dropped. This needs deliberate work: Flask's form
  parser spools any upload over 500 KB to a temporary file by default, so the
  request class must keep files in memory, and Caddy must stream the body
  rather than buffer it. Both are to be checked on the server, not assumed. Only the extracted evidence — matched
  row, sentences, pages, scores — is stored, in the job.
- **Deleted with the job**, seven days after the job was submitted. Never
  cached for reuse by later checks, unlike citing works.
- **No file names stored or logged**; the report shows the matched title.
- **Anyone with the job's link sees the extracted sentences.** The upload form
  says so before anything is sent.
- **Uploads spend no OpenAlex requests** (matching is against rows already
  fetched), so they need a limit of their own, on files an hour across all
  visitors, for the same reason the paper limit is shared rather than per
  person.

**Decision 3 — excerpts are shown.** Short
sentences around each citation, shown only within the job. They are what lets
the reader judge; without them the full-text score is a number without its
derivation.

## How we will know it works

Before the proposal: the open-access comparison studies from the assay pilot
and the ChromBPNet and scPerturb samples, uploaded by hand. For each, did it
find the reference entry and the citing sentences, and does the full text
separate checking the resource from using it where the abstract could not?
This is a smoke test, not a precision measure; that still needs the labelled
sample in the ROADMAP.

## Decisions, settled 2026-11-13

1. Uploads attach to a finished job; there is no standalone form.
2. `pypdf` for extraction, not GROBID.
3. Extracted sentences are shown within the job.
4. Upload limits as under **Input**, sized to the server's memory.
