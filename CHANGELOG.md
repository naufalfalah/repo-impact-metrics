# Changelog

## 1.0.0 — 2026-11-11

First public release.

- Evidence-tier workflow (A verified, B reproducible, C self-reported, D not claimable);
  no invented, rounded-up, or combined numbers.
- `repo_metrics.py` evidence ledger: git ownership, tests, endpoints, data models,
  security, reliability and observability patterns, AI-agent signals, infra.
- Detection of authorization/RBAC, performance mechanisms (index migrations, eager
  loading, pagination), third-party integrations, DB migrations, and deploy/config
  signals (scale-to-zero, health probes, secret scanning, CI caching, rate limits).
- Commit subjects grouped by impact aspect as a memory aid.
- Metric catalog with an architecture & migration section and a mechanism → proving
  metric map.
- User-defined resume rules override the defaults; output in Markdown or the user's
  YAML resume format (e.g. RenderCV).
- `latency_bench.py` for before/after latency on services the user owns.
- Stdlib unittest suite for both scripts.
