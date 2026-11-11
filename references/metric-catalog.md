# Metric catalog

Which numbers a senior reviewer at Google / Meta / a unicorn actually believes, by
project archetype, and where each number comes from. Read the section(s) matching the
repo, then pick the 2–4 metrics that best prove the project's hardest problem was solved.

## Contents
1. The credibility ladder (read first)
2. Metrics that look good but hurt
3. Backend / API services
4. AI agents, LLM apps, RAG
5. Data pipelines & async processing
6. Infra, DevOps & delivery
7. Frontend / full-stack product
8. Team, ownership & delivery (work repos)
9. Converting capability into outcome when there are no users
10. Architecture & migration
11. Mechanism map: what the code shows → the number that proves it → where it lives

---

## 1. The credibility ladder

Rank every candidate metric on this ladder. Resume bullets should use the highest rung
available for each claim.

| Rung | Type | Example | Why reviewers trust it |
|---|---|---|---|
| 5 | Business outcome, attributable | "cut refund processing from 2 days to 4 hours for 3 support staff" | Someone paid for or depended on it |
| 4 | User/usage at real scale | "8K+ registered merchants", "2.1K weekly active" | Hard to fake, easy to check in interview |
| 3 | Measured quality/perf vs. a baseline | "p95 latency 820→190 ms", "category accuracy 89% on 300 labeled support tickets" | Has a denominator and a comparison |
| 2 | Designed capacity / guarantee | "amount matching within 1% tolerance", "idempotent retries, zero duplicate posts in 500-event replay" | Shows judgment; weaker without outcome |
| 1 | Scope / size | "4-agent pipeline", "23 REST endpoints", "4-service Docker Compose stack" | Context only — describes, doesn't prove |
| 0 | Activity | LOC, commit count, "25 tests", hours worked | Measures effort, not result |

Rungs 0–1 may appear as *context inside* a bullet, never as its headline result.

## 2. Metrics that look good but hurt

Flag these when you see them in the user's current resume:

- **Test count** ("25 passing tests"). Small absolute numbers read as small projects.
  Replace with coverage % of the critical module, or what the tests prove
  ("regression suite covering all 6 refund rules").
- **LOC / commits / contributions graph.** Effort, not outcome. Seniors write less code.
- **"100% uptime"** on a hobby deploy with no traffic. Unfalsifiable and naive.
- **Accuracy without a dataset** ("95% accurate"). Ask: on what, how many, labeled by whom?
- **Percentages with a tiny base** ("300% growth" from 3 to 12 users). State the absolute.
- **Model/vendor names as achievement** ("used Gemini 2.5 Flash"). Tools belong in the
  skills line or as the "by doing Z" clause, not as the result.
- **Feature lists** ("dark mode, PWA, responsive"). Table stakes; cut for backend roles.

## 3. Backend / API services

| Metric | Source | How to obtain |
|---|---|---|
| p50/p95/p99 latency, before vs. after an optimization | measured | `scripts/latency_bench.py` on both commits, same flags |
| Throughput (req/s) at acceptable error rate | measured | same, increase `-c` until errors or p95 degrade |
| Query count per request (N+1 removed) | measured | ORM query logging / `EXPLAIN ANALYZE` before vs. after |
| Cache hit rate | measured / prod logs | Redis `INFO stats` keyspace_hits/misses |
| Endpoints, services, tables owned | code | `repo_metrics.py` + git ownership by directory |
| Error rate / incident reduction | prod data | user-provided; ask for dashboard numbers |
| Payload / response size reduction | measured | curl `-w '%{size_download}'` before/after |

The strongest backend bullet pairs one *design decision* with one *measured result*:
"Added Redis read-through cache for rate lookups, cutting p95 from 640 to 110 ms at 50 rps".

## 4. AI agents, LLM apps, RAG

Reviewers for AI roles are skeptical of demos. The metric that separates a serious
project is an **evaluation on a labeled set** — almost nobody at junior/mid level has one.

| Metric | How to obtain |
|---|---|
| Task accuracy / field-level extraction accuracy | Label 50–200 real examples; score exact-match per field |
| Precision / recall of a classifier-like step (e.g. fraud flag, escalation) | Same labeled set; confusion matrix |
| Automation rate (share handled without human) | Run pipeline over labeled set; % auto-approved **and** correct |
| False auto-approve rate | The number a finance or trust reviewer cares about most |
| Retrieval hit@k / MRR for RAG | Build question→source-doc pairs; check whether the source is in top-k |
| Latency per item, cost per item (tokens × price) | Log token usage; `latency_bench.py` for the endpoint |
| Grounding / citation validity rate | Sample outputs; % where cited URL actually supports the claim |
| Guardrail effectiveness | Adversarial/prompt-injection set; % blocked |

When an eval set doesn't exist, the single highest-leverage recommendation is to build
one (often 2–4 hours for 50 examples). Say so plainly. See `measurement-recipes.md` §3.

## 5. Data pipelines & async processing

| Metric | Source |
|---|---|
| Records/documents processed per run or per hour | logs / measured |
| End-to-end latency from event to result | timestamps in logs |
| Duplicate / lost message rate under retry or crash replay | replay test |
| Backfill / reprocessing time | measured |
| Cost per 1K records | cloud billing or estimate from resource usage |

## 6. Infra, DevOps & delivery

| Metric | Source |
|---|---|
| Docker image size before/after multi-stage | `docker images` on both builds |
| CI duration before/after caching | GitHub Actions run history |
| Deploy frequency / lead time | tags, release history, `git log` |
| PR review turnaround (open → first review → merge) | `gh pr list --state merged --json createdAt,mergedAt,reviews` |
| Time from first commit to feature-complete / first release tag | `git log --reverse --format=%ad --date=short \| head -1` vs. tag date |
| Local setup steps / time for a new developer | count steps in README before vs. after Docker Compose + seed scripts; time a fresh `docker compose up` |
| Cold start time (Cloud Run / Lambda) | first-request latency after scale-to-zero |
| Manual steps removed | count steps in old vs. new runbook |
| Secrets moved out of code / env | code (Secret Manager usage) — rung 2 |

## 7. Frontend / full-stack product

Lighthouse performance/accessibility score, bundle size (KB gzip), LCP/INP, conversion or
task-completion rate (user-provided). For backend-targeted resumes keep at most one
frontend metric, and only if it demonstrates a systems decision (e.g. nginx proxy removing
CORS exposure) rather than UI polish.

## 8. Team, ownership & delivery (work repos)

For company code the user cannot share, git history run locally is the evidence:

- Share of commits / churn in the subsystem they claim (`--author` output, top dirs)
- Number of services or modules where they are the top contributor
- PRs reviewed (`gh pr list --search "reviewed-by:@me" --state merged`)
- Standards the user authored and others now follow: ADRs/RFCs, `CONTRIBUTING.md`, PR
  templates, lint/CI baselines (`git log --diff-filter=A --format='%an %ad' -- <path>`
  shows who created them; later commits by others show adoption)
- Onboarding/mentoring outcome: time for a mentee to ship independently
- On-time delivery rate across N projects (must come from their records)

Business outcomes (users, revenue, time saved) must come from the user — dashboards,
reports, stakeholder emails. Never estimate them.

## 9. Converting capability into outcome when there are no users

Portfolio projects rarely have real users. Do not invent usage; instead move up the ladder
from rung 1–2 to rung 3 by *measuring against a realistic workload*:

- "Routes 300 historical support tickets at 89% category accuracy, auto-resolving 42% with
  0 wrong refunds" beats "4-agent support triage bot".
- "Answers 200 questions from a public QA benchmark with hit@5 of 0.82" beats "RAG chatbot
  over company docs".

Name the dataset source so the claim is checkable. These examples are fictional —
propose a dataset only if it actually fits the user's project.

**Pre-launch products** (work or startup code that never reached users) — the repo can
still prove launch readiness:

- Delivery speed and scope: first commit → feature-complete in N weeks, N endpoints,
  N third-party integrations (git + `repo_metrics.py`)
- CI from day one: first CI-config commit date vs. first commit date
- Coverage of the core modules (payment, booking), not whole-repo coverage
- Load capacity vs. projected traffic: a local k6 run against the user's own build
- UAT pass rate, pilot users, demo used for fundraising → Tier C, ask the user

Every number that did not come from production carries its context in the bullet:
"in k6 load tests", "in local benchmarks", "in staging", "on N labeled cases".

## 10. Architecture & migration

Migrations are the most repo-provable senior signal: git history records the before
state, the after state, and how long the transition took. Look for them even when the
user doesn't mention them — commit subjects containing `migrate`, `upgrade`, `split`,
`extract`, `deprecate`, `remove legacy`, `dual write`, `backfill` are the usual trail.

| Metric | Evidence in repo | How to obtain | Tier |
|---|---|---|---|
| Framework/runtime version before → after | dependency manifests | `git log -p -- composer.json package.json pyproject.toml \| grep -E '^[-+].*(laravel/framework\|"next"\|"express"\|django\|fastapi)'` | A |
| Monolith → N services | deployable units at old vs. new SHA | `git ls-tree -r --name-only <sha> \| grep -cE '(^\|/)Dockerfile$'`; compose services at both SHAs | A |
| DB engine / ORM migration | driver deps, migration scripts, backfill or dual-write code | dependency diff + `git log --name-only -- '*migrat*' '*backfill*'` | A (rung 2) |
| Upgrade with no regressions | same suite passes at both SHAs | run tests at old and new SHA | A if run here |
| Duplicated implementations consolidated | N auth/payment/notification modules before vs. after | grep module names at both SHAs | A |
| Migration duration | first → last commit touching the migration paths | `git log --format=%ad --date=short -- <paths> \| sort \| sed -n '1p;$p'` | A |
| Records migrated, downtime, data loss | not in the repo | ask the user (Tier C); the dual-write/verification code makes "zero data loss" defensible | C |

Strongest shape: decision + pattern + safety guarantee + scope.
"Migrated N MongoDB collections to PostgreSQL via dual-writes and backfill validation,
cutting over with zero downtime" — the pattern is Tier A from code; "zero downtime" is
Tier C and must be confirmed.

## 11. Mechanism map

Code shows the *mechanism*; the proving number usually lives somewhere else. For each
mechanism found in step 4, this table says what number would prove it, whether it can be
produced from the repo, and what to ask the user otherwise. The skill does not mine
dashboards, trackers or databases — numbers living there are Tier C questions.

| Mechanism found in code | How to spot it | Proving metric | Where the number lives |
|---|---|---|---|
| Cache layer | `redis`, `Cache::`, `lru_cache`, cache decorators | p95 before/after on the cached endpoint; cache hit rate | `latency_bench.py` at both SHAs (B); APM / Redis `INFO stats` (C) |
| Index added | migrations with `->index(`, `CREATE INDEX`, `add_index`, `db_index=True`, `@@index` | query time before/after | `EXPLAIN ANALYZE` on a local seed at both SHAs (B); slow-query log (C) |
| N+1 removed | `with(`, `load(`, `select_related`, `prefetch_related`, `joinedload`, Prisma `include:` added in a diff | queries per request before/after | ORM query log at both SHAs (B) |
| Work moved to background | queue jobs, `ShouldQueue`, Celery tasks, workers | latency of the endpoint that offloaded | `latency_bench.py` at both SHAs (B) |
| Pagination / batching | `paginate(`, `limit/offset`, cursor params, batch sizes | payload size, memory, calls per run | `curl -w '%{size_download}'` (B); batch constants (A) |
| Idempotency / dedup | idempotency keys, unique constraints, dedup sets | duplicates under replay = 0 | replay test in repo (A) or one the user runs (B) |
| Retry / backoff / DLQ | `tenacity`, `retry`, dead-letter config | failed jobs recovered | tests (A); logs (C) |
| Health checks / rolling deploy | `/health`, readiness probes, `maxUnavailable: 0`, blue-green config | zero-downtime deploys; uptime | config is rung 2 (A); uptime and incidents (C) |
| Observability | structured logging, Sentry, OpenTelemetry, alert rules | MTTR; % incidents caught before users | Tier C — ask |
| Authorization | `Gate::`, policies, `can(`, `@Roles`, permission middleware | endpoints × roles protected | count from code (A) |
| Rate limiting / lockout | `throttle`, `express-rate-limit`, `slowapi`, Nginx `limit_req` | configured limits; attempts blocked | config (A, rung 2); blocked counts (C) |
| Secret hygiene | Secret Manager clients, `gitleaks`/`detect-secrets` pre-commit | hardcoded secrets removed | `git log -p -S '<key prefix>'` count (A) |
| Scale-to-zero / rightsizing | `min-instances: 0`, `minScale`, instance types in IaC | monthly infra cost before/after | config (A, rung 2); billing (C) |
| Multi-stage Docker build | `FROM ... AS builder` | image size before/after | `docker images` at both SHAs (A) |
| CI caching / parallel jobs | `actions/cache`, `needs:`, matrix | CI duration before/after | `gh run list --json durationMs` (A) |
| LLM routing / prompt caching | model switch by task, cache keys on prompts | cost and latency per request | token logs from a small run (B) |
| Third-party integrations | SDK imports: Midtrans, Xendit, Stripe, Twilio, Meta Graph, WhatsApp, Google Maps | number of integrations owned | code + git ownership (A, rung 1) |
| Dev environment | `docker-compose.yml`, seed scripts, Makefile | setup time for a new developer | time a fresh setup (B) |

Rule: a mechanism without its proving number is rung 2 at best. Write the bullet with
`[?N]` for the number and put the "where it lives" question in the report.
