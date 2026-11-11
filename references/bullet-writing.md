# Writing the bullets

## Formula

Google's recruiting guidance: **Accomplished [X] as measured by [Y], by doing [Z].**
In practice, lead with the verb and the result, then the mechanism:

> **Verb** + **what changed / was built** + **measured result** + **how (key tech/decision)**

A reviewer skims the first 8–10 words. Put the number there when it's strong.

## Rules

**Always** (these never relax):

- Every number is Tier A (verified) or confirmed Tier B/C — see SKILL.md. Unconfirmed
  numbers are written as `[?N]` placeholders, never as guesses.
- Numbers are written exactly as measured or reported: never rounded up, summed across
  sources, or combined into a new figure. A number already on the user's resume is reused
  verbatim (their resume says "3K+", the bullet says "3K+").
- Any number not measured in production carries its context inside the bullet:
  "in local benchmarks", "in k6 load tests", "in staging", "on N labeled cases".
- Ownership verbs must match git evidence: "Built" only if the author's commits dominate
  that subsystem; otherwise "Co-built", "Contributed", or scope it ("Built the audit
  module of…").

**Defaults** (the user's own resume rules override these — see SKILL.md):

- Starts with a strong past-tense verb: Built, Designed, Cut, Reduced, Automated, Led,
  Migrated, Scaled. Never "Responsible for", "Worked on", "Helped", "Utilized".
- At most 2 rendered lines (~150 characters); 1 line is better. Split or cut anything
  longer.
- Trailing punctuation matches the user's existing bullets; with nothing to match, no
  trailing period.
- One primary number per bullet; a second only if it's the baseline for the first.
- Tools appear once, as the mechanism — not as a stack dump.
- 3–4 bullets for a recent role/project, 1–2 for older ones.

## Rewrites

The projects below are fictional; each shows one pattern.

**Activity metric → quality metric**
- Weak: Wrote a test suite with 25 passing unit tests and containerized the app with
  Docker
- Why: "25 tests" is rung 0 and reads as small; two unrelated ideas in one bullet.
- Strong: Hardened the payment-retry module with [?N]% branch coverage across every
  failure path, gating each deploy in CI

**Design constant → design constant + outcome**
- Weak: Implemented a fraud-scoring service with a 0.8 risk threshold and a
  manual-review fallback for borderline transactions
- Why: Good judgment (rung 2) but the reader can't tell if it works.
- Strong: Auto-cleared [?N]% of transactions with zero missed fraud cases on [?N] labeled
  transactions, using a 0.8 risk threshold and manual-review fallback

**Architecture description → architecture + why it mattered**
- Weak: Designed a 4-agent architecture (Router, Retriever, Answerer, Critic) on FastAPI
  and LangGraph
- Why: Listing agent names is scope (rung 1). Reviewers ask "why four, not one?"
- Strong: Split support triage into 4 LangGraph agents so an independent critic catches
  wrong answers, raising answer accuracy from [?N]% to [?N]%

**Feature list → cut**
- Weak: Shipped as a responsive, installable Progressive Web App with dark mode support
- Verdict: Remove for backend/platform roles. Use the line for a measured result.

**Outcome without mechanism → add the how**
- Weak: Enabled online ordering for 3K+ restaurant customers
- Strong: Led a 4-engineer team extending an ordering platform serving 3K+ restaurant
  customers, [mechanism found in the repo, e.g. a queue-based order pipeline…]
- Note: the strong version keeps the user's existing facts verbatim (team size,
  "extending", "3K+") and only adds a mechanism the code proves. It does not upgrade
  "extending" to "building" or invent a product type.

## Picking which bullets survive

Rank candidate bullets by: (1) evidence rung, (2) relevance to the target JD, (3) whether
it shows a *decision under a trade-off*. Keep the top 3–4. One bullet per project should
be the "hardest problem" bullet — that's the one interviewers will drill into.

## Output formats

Match the format the user's resume already uses. Under the bullets, list every `[?N]`
with the exact command or question that fills it.

**Markdown** (default when there is nothing to match):

```markdown
**Order Router** — queue-based order routing service
- Cut p95 order-routing latency from [?N] to [?N] ms in local benchmarks by adding a Redis read-through cache
- ...
```

**YAML resume (e.g. RenderCV)** — return entries ready to paste into the user's file,
preserving its structure and indentation. Take names and dates from the user's file;
never invent them. Quote any string containing `: ` or starting with `[`, `*`, `&`, `!`,
`%`, `@`, `` ` ``.

```yaml
      - name: Order Router
        summary: Queue-based order routing service
        highlights:
          - Routed [?N]% of orders without manual review on [?N] replayed orders, using idempotent retries
          - ...
```

**Evidence comments.** When the bullets go into a file the user maintains and the format
allows comments, put the evidence directly under each bullet that carries a number, so it
can still be defended months later. It is evidence, never bullet text:

```yaml
        highlights:
          - Cut p95 latency on /orders from 640 to 110 ms in local benchmarks by adding a Redis read-through cache
          # source: Tier B — latency_bench.py -n 300 -c 10, SHA a1b2c3d vs e4f5g6h
```

If the user's resume file has schema problems (for RenderCV: duplicate keys, `date`
alongside `start_date`/`end_date`), point them out in one line; if a skill for that
resume format is available, defer to it for the full rules.
