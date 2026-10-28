# Coding principles

Carried over from CFCR, where they were earned rather than chosen.

No features beyond what was asked. No speculative abstractions, configurability,
or error handling for impossible scenarios.

* Surgical changes. Touch only what the task requires. Don't improve adjacent
  code, comments, or formatting. Match existing style.
* Surface tradeoffs before coding. If multiple interpretations exist, present
  them — don't pick silently. If something is unclear, ask.
* If you notice unrelated dead code or issues, mention them — don't silently
  fix them.

# What this tool may and may not assert

WhoChecked reports; it does not conclude. The distinction is the whole design
and it is easy to erode one commit at a time.

* **A score ranks, it does not classify.** "Which citing papers are
  evaluations" has no ground truth to classify against. Any threshold is a
  section boundary for a reader, never an admission rule.
* **Independence is derived, never asserted.** It comes from author overlap
  between a resource's primary paper and the papers that evaluate it, and the
  derivation is shown alongside every number it produces.
* **Absence is not evidence.** No citing works found, no abstract, no reference
  list, a 404 from a full-text endpoint — each means *unknown*, and must render
  as unknown. Recording one as "not independently evaluated" turns a gap in
  OpenAlex into a claim about a researcher's work.
* **Show the uncertainty in the output.** A weak author match, a venue type
  with known-poor reference metadata, a resolved-by-title paper — the user has
  to be able to see these. A number whose interpretation is false is worse than
  no number, because it looks like a finding.

# Reviewing for exposure

This repository is public and its history is permanent, so every code or
documentation review ends with one question: did this change publish something
personal? Rewriting history afterwards does not retract what was already
cloned.

**Check the diff, never the tree.** The cost has to scale with the change, not
with the repository. One pipeline answers it:

```bash
git diff "$(git merge-base HEAD origin/main)" -U0 | grep '^+' | grep -inEf .github/exposure-patterns.txt
```

Added lines only, and that is the point: something already public is not news,
and a check that re-reports it every time teaches you to ignore it. Exit status
1 with no output means the diff is clean.

The patterns live in `.github/exposure-patterns.txt` so this file does not have
to contain the strings it is looking for. That file holds **one extended regex
per line and nothing else** — `grep -f` has no comment syntax, so a `#` line is
a pattern and a blank line is a pattern that matches everything.

**Known and deliberate, so not findings:** the git author identity on every
commit, and the `Co-Authored-By: Claude …` trailer, whose address is
Anthropic's no-reply attribution address rather than a contact for anyone —
it records that a commit was written with Claude, which is deliberate. Nothing
else yet — add to this list only with a reason, as CFCR does.

Everything else that matches is a finding. In particular:

* A **token or key** of any shape. An OpenAlex API key is required to run this
  tool at all, which makes this the likeliest mistake in the project: it is read
  from the environment, never committed, and never pasted into an issue.
* An **absolute path carrying a username** — a Windows user directory, a Unix
  home directory, a macOS user directory — in code, a docstring, or a commit
  message. Described rather than spelled out, so this file stays clean under
  its own check.
* A **contact address** that is not a deliberate, single, documented one.
* A **real person's name, institution or affiliation** written into a comment
  or a commit message.

**User-submitted input is a separate question from exposure, and a sharper one
than CFCR has.** This tool is given DOIs by strangers, and what someone is
checking can be sensitive — an unpublished competitor's model, a reviewer
checking a manuscript under embargo. Queries must not be logged in a way that
links an input to a submitter, must not appear in URLs that leak through
referrers, and must not be committed as test fixtures. Author names retrieved
from publisher metadata are open bibliographic data; a *query* is not.
