# repo-impact-metrics

A Claude skill that turns a code repository into **resume bullets backed by evidence**.

Engineers usually describe what they built ("4-agent architecture", "25 tests"). Hiring
reviewers look for what changed because of it, with a number they can question. This
skill reads the code and git history, finds the 2–3 hard problems you actually solved,
measures what can be measured, and writes bullets built only from verified facts.
Every number is traced to a file, a command, or your own confirmation. It never makes
numbers up.

## What you get

For each repository, Claude produces:

- **An evidence ledger**: every claimable fact with its source (`file:line`, a command, or
  "confirmed by you") and an evidence tier.
- **Hard problems found in the code**: the decision made for each, and the number that
  would prove it worked.
- **Metrics to obtain**: copy-paste commands or targeted questions for every gap.
- **Draft bullets** in your resume's format (Markdown, or YAML such as
  [RenderCV](https://github.com/rendercv/rendercv)), with `[?N]` placeholders where a
  number still needs proof.

### Evidence tiers

| Tier | Meaning | On the resume? |
|---|---|---|
| **A: Verified** | Read from code, git, or a run Claude executed | Yes |
| **B: Reproducible** | Claude gave you a command; you ran it and reported the output | Yes, once reported |
| **C: Self-reported** | Only you know it (users, revenue, outcomes) | Yes, once you confirm it and can defend it in an interview |
| **D: Not claimable** | Unverifiable, vanity (LOC, commit count), or contradicted by the code | No |

## Install

**Claude Code (all projects):**

```bash
git clone https://github.com/naufalfalah/repo-impact-metrics ~/.claude/skills/repo-impact-metrics
```

**Claude Code (one project only):** clone into `<project>/.claude/skills/repo-impact-metrics`.

**claude.ai:** download `repo-impact-metrics.zip` from the
[latest release](https://github.com/naufalfalah/repo-impact-metrics/releases/latest), then
upload it in **Settings → Capabilities → Skills**.

## Usage

Ask in plain language; the skill triggers on requests like:

- "What metrics can I put on my resume from this repo?" + a GitHub URL or a local path
- "Help me write resume bullets for this project"
- "Prove this result with data"
- "Cari metrik dampak dari repo ini" (Indonesian prompts work too)

**Code you can't share** (a past employer's repo): Claude hands you
`scripts/repo_metrics.py` to run on your own machine. It prints aggregate counts and file
paths only, no source code. Check your employer's policy before pasting the output back.

## Bring your own resume rules

The skill ships with sensible defaults (verb-first, ≤2 lines, one primary number per
bullet). If you keep your own rules (in `CLAUDE.md`, a claude.ai Project's instructions,
or a resume template), **your rules win**. For example:

```markdown
## Resume rules
- Bullets: 100–140 characters, hard cap 180, no trailing period
- Output: RenderCV YAML matching my existing files
- Every bullet with a number gets a `# source:` comment underneath
```

Two rules can never be relaxed: no invented numbers, and no rounding up or combining
numbers.

## The scripts (usable on their own)

Both scripts are Python standard library only. Nothing to install.

**`scripts/repo_metrics.py`**: builds the evidence ledger for a local checkout.

```bash
python3 scripts/repo_metrics.py /path/to/repo --author "you@example.com" --json ledger.json
```

It reports git ownership (commit share, churn by directory), tests, endpoints, data
models, security and reliability patterns, performance mechanisms (index migrations,
eager loading, pagination), third-party integrations, DB migrations, deploy and config
signals (scale-to-zero, health probes, secret scanning, CI caching), design constants,
README claims to verify, and **your commit subjects grouped by impact aspect**. That last
section is usually where forgotten migrations and performance fixes show up:

```text
## Commit subjects by aspect (author you@example.com, 9 commits) — memory aid; read each diff before claiming
- **performance**: 1 commits, 2024-03-02 → 2024-03-02
  - f10518d 2024-03-02 perf: add index on tx.user_id to fix slow listing
- **architecture migration**: 1 commits, 2024-04-11 → 2024-04-11
  - 24766ae 2024-04-11 refactor: migrate leads from MongoDB to PostgreSQL with backfill
```

**`scripts/latency_bench.py`**: p50/p95/p99 latency and throughput for a service *you*
run, for before/after comparisons.

```bash
python3 scripts/latency_bench.py http://localhost:8000/health -n 300 -c 10
```

## Safety and privacy

- `repo_metrics.py` is read-only: it reads files and runs `git log`. It makes no network
  calls.
- `latency_bench.py` is meant for hosts you own. Requests are capped at 5,000 per run.
- The skill does not mine dashboards, trackers, billing, or production databases. When
  the proving number lives there, it asks you instead.
- The skill will not run anything that needs production credentials, and will not loop a
  paid API without your consent.

## Limitations

- Pattern counts are regex heuristics. The skill spot-checks cited numbers against the
  referenced `file:line`, and you should too.
- Commit-subject grouping depends on how descriptive your commit messages are.
- Business outcomes (users, revenue, time saved) can't come from a repo. They are always
  Tier C and need your confirmation.

## Repository layout

```text
SKILL.md                       skill instructions Claude follows
references/
  metric-catalog.md            credibility ladder, metrics by project type, mechanism → proof map
  measurement-recipes.md       commands for coverage, latency, LLM evals, git ownership
  bullet-writing.md            bullet formula, rules, rewrites, output formats
scripts/
  repo_metrics.py              evidence ledger extractor
  latency_bench.py             latency/throughput benchmark
tests/                         stdlib unittest suite for both scripts
```

## Development

```bash
python3 -m unittest discover -s tests -v
```

CI runs the suite on Python 3.9–3.13. When you add a detection pattern, add a fixture line
for it in `tests/test_repo_metrics.py`.

## License

[MIT](LICENSE)
