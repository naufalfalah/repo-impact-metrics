---
name: repo-impact-metrics
description: Deep-review a code repository (the code, git history, tests, infra) and extract evidence-backed impact metrics that can be written as resume bullets, then draft those bullets in the format the user's resume uses (Markdown, or YAML such as RenderCV). Use this skill whenever the user wants to turn a repo or project into resume content — phrasings like "ulas repo saya untuk resume", "cari metrik dampak dari repo ini", "apa angka yang bisa saya tulis di CV dari project ini", "quantify my project", "what metrics can I put on my resume", "help me write resume bullets for this project", "prove this result with data", or when the user pastes a github.com URL / uploads a repo zip and mentions resume, CV, bullets, impact, achievements, or STAR. Also use when resume entries have empty highlights and the user wants to fill them from their work code. Do NOT use for portfolio packaging (pinning repos, README polish, profile look) or for PR/diff code review.
---

# Repo → Resume Impact Metrics

Turn a repository into resume bullets a skeptical senior reviewer believes. The product of
this skill is not a code review; it is an **evidence ledger** (every claimable fact, with
its source) and a set of bullets built only from that ledger.

The core problem this solves: engineers describe *what they built* ("4-agent
architecture", "25 tests") because that's what they remember. Reviewers at top-tier
companies hire on *what changed because of it*, with a denominator. The gap is closed by
reading the code for the decisions that mattered, then measuring them — not by picking
more impressive-sounding words.

## The user's own rules win

Users often keep resume rules somewhere: project instructions (`CLAUDE.md`, a claude.ai
Project's instructions), a resume template, or a style guide. Look for them in step 1.
Where they set bullet length, punctuation, bullet counts, output format, or how numbers
must be sourced, they override the defaults in this skill and its references. The
non-negotiables below never relax — a user rule can only make them stricter.

## Non-negotiable: no invented numbers

A fabricated metric is worse than no metric: interviewers drill into every number, and one
that collapses under "how did you measure that?" costs the whole interview. So:

- Every number in a final bullet carries a tier (below). Anything not Tier A or
  user-confirmed B/C is written as `[?N]` with the command or question that fills it.
- Never estimate users, revenue, time saved, or accuracy. Ask.
- README claims are hypotheses, not evidence. Verify them against code or a run.
- Never round up, sum, or combine numbers. A number the user already wrote on their
  resume is reused verbatim (their resume says "3K+" → the bullet says "3K+").
- A number not measured in production names its context in the bullet: "in local
  benchmarks", "in k6 load tests", "in staging", "on N labeled cases".

**Scope of this skill:** evidence comes from the repository: code, git history, tests,
CI, PRs. It does not mine dashboards, trackers, billing or production databases. When the
proving number lives there, the skill names the mechanism, writes `[?N]`, and asks the
user (Tier C).

| Tier | Meaning | Allowed on resume? |
|---|---|---|
| **A — Verified** | Read from code, git, or a run you executed here | Yes |
| **B — Reproducible** | You provided a command; user ran it and reported the output | Yes, once reported |
| **C — Self-reported** | Only the user knows (users, revenue, stakeholder outcomes) | Yes, once the user confirms and can back it in interview |
| **D — Not claimable** | Unverifiable, vanity (LOC, commit count), or contradicted by code | No |

## Workflow

### 1. Load context before touching code

- **The user's resume rules.** Check for project instructions or a template that sets
  resume rules (see "The user's own rules win"). Note the output format they use.
- **Target role.** If the user keeps a career-strategy document and a connector to it is
  available, read it live and note its last-updated date; otherwise ask for, or infer
  from the conversation, the target role or JD. The role decides which metrics matter (a
  backend role values p95 and correctness; an AI role values eval accuracy).
- **Current resume entry.** Read the user's existing entry for this project/role,
  wherever they keep it (resume files in the workspace, an uploaded CV, or pasted text).
  Current bullets tell you what the user believes is impressive — useful for spotting the
  gap — and hold numbers that must be reused verbatim.

### 2. Get the code

- Public repo: `git clone --filter=blob:none <url>` (full history, lazy blobs). Never
  `--depth 1` — ownership and timeline stats need history.
- Private repo: ask for a zip upload (include `.git` if possible) or a read-only token.
- **Company code the user can't share** (common for past employers): switch to *local
  mode*. Give them `scripts/repo_metrics.py` (stdlib, no install) plus the command block
  in `references/measurement-recipes.md` §5, have them run it on their machine and paste
  the output. The ledger contains aggregate counts and paths, not source. Remind them to
  follow their employer's policy.

### 3. Build the evidence ledger

```bash
python3 scripts/repo_metrics.py <repo> --author "<name-or-email>" --json ledger.json
```

Find the author string first with `git -C <repo> shortlog -sne --no-merges | head`. The
script reports stack and LOC, git ownership (share of human commits, churn by directory),
tests, endpoints, data models, AI-agent signals, async/reliability/security patterns
(including authorization/RBAC), performance mechanisms (index migrations, eager loading,
pagination), third-party integrations (payment, messaging, Meta, storage SDKs), DB
migration files, deploy & config signals (scale-to-zero, health probes, secret scanning,
CI caching, rate-limit config), infra (Dockerfiles, compose services, CI jobs), design
constants (thresholds, tolerances, limits with file:line), numeric claims in the README,
and **commit subjects bucketed by impact aspect** (architecture/migration, performance,
reliability, security, testing, delivery, integrations, cost, AI). Use that last section
as the starting list for step 4 — it surfaces work the user forgot — but read each diff
before claiming anything from it.

Counts are regex heuristics. Spot-check any number you intend to cite by opening the
referenced file:line. Treat author ownership seriously: if the user claims "built X" but
their churn is concentrated elsewhere, the bullet must be scoped to what they did.

### 4. Read the code for the decisions that matter

Metadata can't tell you what was hard. Open the entry points, the core domain module, and
the most-churned files by the author. You are looking for **2–3 hard problems** and the
decision made for each:

- **Correctness under failure** — retries, idempotency, transactions, what happens when
  the LLM/API returns garbage or times out
- **Data integrity** — validation boundaries, money/decimal handling, deduplication
- **Scale & latency** — caching, batching, async/queues, N+1 avoidance, pagination
- **Cost & safety (AI)** — model choice, structured output, grounding, guardrails,
  confidence thresholds, human escalation
- **Security** — secret handling, authz boundaries, what user data is persisted
- **Architecture & migration** — monolith splits, DB or framework migrations,
  consolidated duplicates. Git history holds the before state, the after state and the
  duration; scan commit subjects for `migrate`, `upgrade`, `split`, `extract`,
  `backfill`, `dual write`, `remove legacy` (catalog §10)

For each, note file:line, the trade-off, and *what number would prove it worked* —
`references/metric-catalog.md` §11 maps each mechanism to its proving number and where
that number lives. Also note weaknesses honestly (no tests on the critical path, secrets
in repo, dead code) — they change what can be claimed and what the user will be asked in
interview.

### 5. Measure what's missing

Pick the proving metric for each hard problem from `references/metric-catalog.md` (read
the section for this project's archetype, plus §11 for every mechanism found in step 4).
Then:

- Run in the sandbox what's safe and self-contained: tests + coverage, image size,
  offline evals with committed fixtures. Record the command and commit SHA.
- Hand the user copy-paste commands for the rest (`references/measurement-recipes.md`),
  e.g. `scripts/latency_bench.py` against their local service, or an eval harness.
- For AI projects without an eval set, recommend building one (50–200 labeled cases)
  as the single highest-leverage task. It's usually the difference between a demo and a
  credible project.

Don't run anything needing production credentials, paid-API loops without consent, or load
against hosts the user doesn't own.

### 6. Interview the user — briefly and specifically

Ask at most ~5 questions, each tied to a `[?N]` or an ownership ambiguity. Always include
one of each of these, phrased for the specific project:

- *"What was the hardest technical challenge here?"* — then check whether the code agrees
- *"How can we prove this result with data?"* — for the claim they care most about

Good questions name the thing: "Git shows you touched `billing/` most — did you design the
reconciliation flow or extend it?" beats "Tell me about your role."

### 7. Write bullets

Follow `references/bullet-writing.md`: verb-first, short, one primary number, mechanism
named once, ownership verb matched to git evidence. Output in the format the user's resume
uses (step 1): paste-ready entries for a YAML resume such as RenderCV, otherwise a
Markdown list. When the bullets go into a file the user maintains and the format allows
comments, put a `# source:` comment under each bullet that carries a number (tier +
file:line, command, or "confirmed by user"). The user's own resume rules win over the
defaults in `bullet-writing.md`.

## Report structure

Write the report in the user's language; keep bullets in the resume's language (usually
English).

```markdown
[1–2 sentences: what was inspected (repo, commit SHA, author filter) and the headline
finding — usually "the strongest claimable result is X; the biggest missing proof is Y"]

## Evidence ledger (claimable facts)
| Fact | Value | Source (file:line / command) | Tier |

## Hard problems found in the code
[2–3 items: problem → decision → file:line → the metric that would prove it]

## What the current resume gets wrong
[Specific: which existing bullets use rung-0/1 metrics, overclaim ownership, or miss the
strongest result. Skip if there is no existing entry.]

## Metrics to obtain
[Each [?N]: why it matters, exact command or question, ~time cost. Ordered by leverage.]

## Draft bullets
[In the user's resume format. Then: for each [?N], what fills it.]

## Questions for you
[≤5, specific]
```

## Standards of honesty

- **Rank by evidence, not by how impressive it sounds.** A rung-3 measured result beats a
  rung-1 architecture description every time, even if the description sounds grander.
- **Say when a project isn't resume-worthy for the target role.** If a repo has no hard
  problem and no measurable result, recommend cutting it or naming what would make it
  worthy. Padding a one-page resume with weak projects costs strong bullets their space.
- **Scope team work truthfully.** "Led" requires evidence of leadership (the user's
  confirmation plus e.g. review activity); "Built" requires dominant ownership.
- **Name the interview risk.** For each final bullet, you should be able to say what the
  interviewer will ask next. If the user couldn't answer it, the bullet isn't ready.

## Files

- `scripts/repo_metrics.py` — evidence ledger extractor (stdlib; safe to give the user to
  run locally). `--help` for options.
- `scripts/latency_bench.py` — p50/p95/p99 + throughput for the user's own service.
- `references/metric-catalog.md` — credibility ladder, vanity metrics, metrics by project
  archetype, architecture & migration (§10), mechanism → proving metric map (§11). Read
  before choosing metrics.
- `references/measurement-recipes.md` — commands for coverage, latency, LLM evals, image
  size, and git ownership on private repos. Read before step 5.
- `references/bullet-writing.md` — bullet formula, default rules, rewrites, output
  formats. Read before step 7.
