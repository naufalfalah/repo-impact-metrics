#!/usr/bin/env python3
"""
repo_metrics.py — sweep a local repository and emit an *evidence ledger*:
facts that can be verified from code and git history, each with a source.

It deliberately does NOT produce resume bullets or impact claims. Its job is
to give the reviewer hard, citable numbers and pointers (file:line) so that
every metric later written on a resume can be traced back to evidence.

Usage:
    python3 repo_metrics.py <repo_path> [--author "name or email"] [--json out.json]

Stdlib only. Safe to run on any checkout (read-only; runs `git log` only).
"""
import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime

SKIP_DIRS = {
    ".git", "node_modules", "vendor", "dist", "build", ".next", ".nuxt", "out",
    ".venv", "venv", "env", "__pycache__", ".pytest_cache", ".mypy_cache",
    "coverage", ".turbo", ".idea", ".vscode", "target", "bower_components",
    ".terraform", "storage", "public/build", ".svelte-kit", ".astro",
}
SKIP_FILES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "composer.lock",
    "poetry.lock", "Pipfile.lock", "uv.lock", "Cargo.lock", "go.sum",
}
MAX_FILE_BYTES = 1_000_000
# generated/minified code inflates every count; never attribute it to the author
GENERATED_RE = re.compile(r"(\.gen\.|\.generated\.|\.min\.(js|css)$|_pb2\.py$|\.pb\.go$|\.d\.ts$)")

LANG_BY_EXT = {
    ".py": "Python", ".ts": "TypeScript", ".tsx": "TypeScript (TSX)",
    ".js": "JavaScript", ".jsx": "JavaScript (JSX)", ".mjs": "JavaScript",
    ".cjs": "JavaScript", ".php": "PHP", ".go": "Go", ".java": "Java",
    ".kt": "Kotlin", ".rb": "Ruby", ".rs": "Rust", ".cs": "C#", ".dart": "Dart",
    ".swift": "Swift", ".vue": "Vue", ".svelte": "Svelte", ".astro": "Astro",
    ".sql": "SQL", ".sh": "Shell", ".html": "HTML", ".css": "CSS",
    ".scss": "SCSS", ".tf": "Terraform", ".blade.php": "Blade",
    ".prisma": "Prisma",
}
# non-code languages whose files are still scanned by the pattern families
SCHEMA_LANGS = {"SQL", "Terraform", "Prisma"}
CODE_LANGS = {"Python", "TypeScript", "TypeScript (TSX)", "JavaScript",
              "JavaScript (JSX)", "PHP", "Go", "Java", "Kotlin", "Ruby", "Rust",
              "C#", "Dart", "Swift", "Vue", "Svelte", "Astro"}

PY = {"Python"}
JS = {"TypeScript", "TypeScript (TSX)", "JavaScript", "JavaScript (JSX)", "Vue", "Svelte", "Astro"}
PHP = {"PHP"}

# ---------- pattern families (count occurrences, keep a few examples) ----------
PATTERNS = {
    "api_endpoints": [
        ("FastAPI/Flask route", r"@\w+\.(get|post|put|patch|delete|route|websocket)\(\s*[\"']", PY),
        ("Express/Hono route", r"(?<!@)\b(?:app|router|r|api|server)\.(get|post|put|patch|delete|all)\(\s*[\"'`]/", JS),
        ("NestJS route", r"@(Get|Post|Put|Patch|Delete)\(\s*[\"'`)]", JS),
        ("Laravel route", r"Route::(get|post|put|patch|delete|resource|apiResource|match|any)\(", PHP),
        ("Django path", r"\b(re_)?path\(\s*r?[\"']", PY),
        ("GraphQL resolver/type", r"\b(type\s+(Query|Mutation)\s*\{|@(Query|Mutation|Resolver)\()"),
    ],
    "data_models": [
        ("SQLAlchemy table model", r"class\s+\w+\(\s*(?:\w+\.)?(?:Base|DeclarativeBase|db\.Model)\s*[,)]", PY),
        ("SQLModel table", r"class\s+\w+\([^)]*\btable\s*=\s*True", PY),
        ("Pydantic/SQLModel schema (non-table)", r"class\s+\w+\((?:(?!table\s*=)[^)])*\b(?:BaseModel|SQLModel)\b(?:(?!table\s*=)[^)])*\)\s*:", PY),
        ("Django model", r"class\s+\w+\(\s*models\.Model\s*\)", PY),
        ("Eloquent model", r"class\s+\w+\s+extends\s+(?:Model|Authenticatable)\b", PHP),
        ("Mongoose schema", r"new\s+(?:mongoose\.)?Schema\s*\(", JS),
        ("Prisma model", r"^\s*model\s+\w+\s*\{"),
        ("TypeORM entity", r"@Entity\("),
    ],
    "tests": [
        ("pytest test fn", r"^\s*(?:async\s+)?def\s+test_\w+\s*\(", PY),
        ("JS/TS it()/test()", r"(?<![\w.])(?:it|test)(?:\.each\([^)]*\))?\s*\(\s*[\"'`]", JS),
        ("PHPUnit test", r"(?:public\s+function\s+test\w+|@test\b|#\[Test\])", PHP),
        ("Pest test", r"^\s*(?:it|test)\(\s*['\"]", PHP),
        ("Go test", r"^func\s+Test\w+\s*\(\s*t\s+\*testing\.T", {"Go"}),
    ],
    "ai_agents": [
        ("ADK agent", r"\b(?:LlmAgent|Agent|SequentialAgent|ParallelAgent|LoopAgent)\s*\(\s*(?:\n\s*)?name\s*="),
        ("LangChain/LangGraph", r"\b(?:StateGraph|AgentExecutor|create_react_agent|RunnableSequence)\b"),
        ("LLM model id", r"[\"'](gemini-[\w.\-]+|gpt-[\w.\-]+|claude-[\w.\-]+|gemma-[\w.\-]+|llama[\w.\-]*)[\"']"),
        ("Tool/function declared to LLM", r"(?:FunctionTool\(|@tool\b|tools\s*=\s*\[)"),
        ("Embedding / vector store", r"\b(?:embed_content|embeddings?\.create|TextEmbedding|VectorSearch|pgvector|Chroma|FAISS|Pinecone|Qdrant|Weaviate|vector_search)\b"),
        ("Structured output schema", r"(?:response_schema|response_format|with_structured_output)"),
    ],
    "async_and_messaging": [
        ("Queue / broker", r"\b(?:amqplib|pika|RabbitMQ|kafka|KafkaProducer|PubSub|pubsub_v1|SQS|Bull(?:MQ)?|Celery|dispatch\(|ShouldQueue)\b"),
        ("Cache", r"\b(?:redis|Redis|ioredis|Cache::|lru_cache|cachetools|memcached)\b"),
        ("Realtime", r"\b(?:socket\.io|Socket\.IO|WebSocket|websockets|SSE|EventSource)\b"),
        ("Scheduler / cron", r"\b(?:cron|APScheduler|node-cron|schedule\(|Cloud Scheduler)\b"),
    ],
    "reliability": [
        ("Retry / backoff", r"\b(?:retry|retries|backoff|tenacity|Retry\()"),
        ("Timeout", r"\btimeout\s*[=:]"),
        ("Rate limit", r"\b(?:rate.?limit|throttle|slowapi|express-rate-limit)\b"),
        ("Idempotency", r"\bidempoten"),
        ("Circuit breaker", r"\bcircuit.?breaker\b"),
        ("Transaction", r"\b(?:transaction\(|begin_nested|DB::transaction|session\.begin|atomic\()"),
    ],
    "security": [
        ("AuthN (JWT/OAuth/session)", r"\b(?:jwt|JWT|OAuth2|oauth|passport|Sanctum|bcrypt|argon2|passlib)\b"),
        ("Input validation", r"\b(?:zod|Joi|yup|class-validator|Validator::make|FormRequest|field_validator|validator\()"),
        ("Secret manager", r"\b(?:secretmanager|Secret Manager|SecretsManager|KeyVault)\b"),
        ("CORS config", r"\b(?:CORSMiddleware|cors\(|allow_origins)\b"),
        ("Authorization (RBAC / policy)",
         r"(?:Gate::|->can\(|\$this->authorize\(|middleware\(\s*\[?\s*['\"](?:can|role|permission):|"
         r"@Roles\(|@UseGuards\(|\bhasRole\(|\bhasPermission\(|permission_required|"
         r"\bIsAdminUser\b|has_permissions?\(|\bauthorize\()"),
    ],
    # mechanisms whose proving number is a before/after measurement (catalog §11)
    "performance": [
        ("Index in migration/schema",
         r"(?:->index\(|->unique\(|CREATE\s+(?:UNIQUE\s+)?INDEX|\badd_index\b|db_index\s*=\s*True|"
         r"models\.Index\(|@@index|@Index\(|\bindex\s*=\s*True|\.index\(\s*\{)"),
        ("Eager loading (N+1 guard)",
         r"(?:::with\(|->with\(\s*['\"\[]|->load\(\s*['\"\[]|select_related\(|prefetch_related\(|"
         r"joinedload\(|selectinload\(|\binclude\s*:\s*\{|\.populate\()"),
        ("Pagination",
         r"(?:->(?:simple|cursor)?[pP]aginate\(|\bPaginator\b|\bpaginate\(|page_size\s*[=:]|"
         r"PageNumberPagination|LimitOffsetPagination|\.skip\(\s*\w|\btake\s*:\s*[\w.]+)"),
    ],
    # third-party APIs owned — rung 1 scope evidence (catalog §11)
    "third_party_integrations": [
        ("Midtrans", r"(?i)\bmidtrans\b"),
        ("Xendit", r"(?i)\bxendit\b"),
        ("Stripe", r"(?i)\bstripe\b"),
        ("PayPal", r"(?i)\bpaypal\b"),
        ("Square", r"(?i)\b(?:squareup|square\.com|square_connect)\b"),
        ("Twilio", r"(?i)\btwilio\b"),
        ("WhatsApp", r"(?i)\bwhatsapp\b"),
        ("Meta / Facebook Graph", r"(?i)(?:graph\.facebook\.com|facebook[-_]business|facebook-nodejs|\bleadgen\b)"),
        ("Telegram", r"(?i)(?:api\.telegram\.org|\btelegraf\b|python-telegram-bot|node-telegram-bot)"),
        ("Google Maps", r"(?i)(?:maps\.googleapis|@googlemaps|\bgooglemaps\b)"),
        ("SendGrid / Mailgun / SES", r"(?i)\b(?:sendgrid|mailgun|client-ses|ses_client|aws-sdk/client-ses)\b"),
        ("Firebase", r"(?i)\bfirebase(?:-admin)?\b"),
        ("AWS S3 / GCS storage", r"(?i)(?:@aws-sdk/client-s3|boto3\.client\(\s*['\"]s3|google\.cloud\s+import\s+storage|@google-cloud/storage|Storage::disk\(\s*['\"](?:s3|gcs))"),
        ("Slack", r"(?i)(?:slack_sdk|@slack/|hooks\.slack\.com)"),
    ],
    "observability": [
        ("Structured logging", r"\b(?:structlog|pino|winston|logging\.getLogger|Log::)\b"),
        ("Metrics / tracing", r"\b(?:prometheus|opentelemetry|OpenTelemetry|statsd|Cloud Trace|datadog)\b"),
        ("Error tracking", r"\b(?:sentry|Sentry|bugsnag|rollbar)\b"),
    ],
}

# numeric design decisions worth citing (thresholds, tolerances, limits)
CONSTANT_RE = re.compile(
    r"(?i)\b([A-Z_]*(?:THRESHOLD|TOLERANCE|CONFIDENCE|TIMEOUT|MAX_RETRIES|RETRIES|TTL|"
    r"LIMIT|BATCH_SIZE|TOP_K|CHUNK_SIZE|WORKERS|CONCURRENCY|RATE)[A-Z_]*)\s*[:=]\s*"
    r"([0-9]+(?:\.[0-9]+)?)"
)
# numbers in prose that look like performance/impact claims
CLAIM_RE = re.compile(
    r"(?i)(\d[\d.,]*\s?(?:%|ms|s\b|sec|seconds|x\b|×|users|requests|rps|qps|req/s|"
    r"tests?|agents?|endpoints?|invoices|documents|files|k\b|K\b|hours?|minutes?))"
)

# DB schema migrations: each one is a dated, attributable change (catalog §10/§11)
MIGRATION_PATH_RE = re.compile(
    r"(?:^|/)(?:database/migrations|migrations|alembic/versions|prisma/migrations|db/migrate)/")

# deploy/config signals that live in YAML/TOML/HCL/conf files, not in code
CONFIG_EXTS = (".yaml", ".yml", ".toml", ".tf", ".json", ".conf")
CONFIG_SIGNALS = {
    "scale_to_zero": r"(?:min-?instances\s*[:=]\s*[\"']?0\b|minScale\s*[:=]\s*[\"']?0\b|"
                     r"min_instance_count\s*=\s*0\b|--min-instances[= ]0\b)",
    "health_probes": r"(?:readinessProbe|livenessProbe|startupProbe|^\s*healthcheck\s*:|^\s*HEALTHCHECK\s)",
    "zero_downtime_rollout": r"(?:maxUnavailable\s*:\s*0\b|blue.?green|\bcanary\b)",
    "secret_scanning": r"(?i)(?:gitleaks|detect-secrets|trufflehog)",
    "ci_caching": r"(?:actions/cache@|\bcache:\s*\n\s*(?:key|paths)\s*:|cache-from)",
    "rate_limit_config": r"(?:\blimit_req(?:_zone)?\b|\brate_limit\s*[:=])",
}
CONFIG_SIGNALS_RE = {k: re.compile(v, re.M) for k, v in CONFIG_SIGNALS.items()}

# commit subjects → impact aspect. A memory aid that surfaces migrations, perf work and
# incidents the user forgot; every hit still needs its diff read before it is claimed.
COMMIT_ASPECTS = {
    "architecture_migration": r"\b(?:migrat|upgrad|split|extract|decoupl|monolith|microservice|"
                              r"rewrite|deprecat|legacy|dual.?write|backfill|consolidat|replatform)",
    "performance": r"\b(?:perf\b|performance|optimi[sz]|speed ?up|faster|latency|slow|redis|caching|"
                   r"cached|cache (?:layer|hit|invalidat|warm)|memoi[sz]|index|"
                   r"n\+1|eager|pagina|batch|memory leak|throughput)",
    "reliability": r"\b(?:retry|retries|idempot|dedup|timeout|fallback|resilien|circuit|health.?check|"
                   r"graceful|race condition|deadlock|incident|hotfix|rollback|monitor|alert|sentry)",
    "security": r"\b(?:secur|authori[sz]|authenti|permission|rbac|jwt|oauth|csrf|xss|sql.?inject|"
                r"saniti[sz]|vulnerab|cve-|secret|encrypt|rate.?limit|throttl)",
    "testing": r"\b(?:tests?\b|testing|spec\b|coverage|e2e|regression suite)",
    "delivery_ci": r"\b(?:ci\b|cd\b|ci/cd|pipeline|deploy|dockeri[sz]|dockerfile|compose|"
                   r"github actions|gitlab.?ci|jenkins|release)",
    "integrations": r"\b(?:webhook|integrat|sdk\b|midtrans|xendit|stripe|twilio|whatsapp|"
                    r"facebook|meta lead|firebase|payment gateway)",
    "cost": r"\b(?:cost|cheaper|billing|rightsiz|scale.?to.?zero|min.?instances|image size)",
    "ai_llm": r"\b(?:llm|prompt|agent|evals?\b|embedding|rag\b|gemini|openai|gpt|claude)",
}
COMMIT_ASPECTS_RE = {k: re.compile(v, re.I) for k, v in COMMIT_ASPECTS.items()}
MAX_COMMIT_EXAMPLES = 6


def iter_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        rel = os.path.relpath(dirpath, root)
        dirnames[:] = [d for d in dirnames
                       if d not in SKIP_DIRS and os.path.join(rel, d).lstrip("./") not in SKIP_DIRS]
        for f in filenames:
            if f in SKIP_FILES or GENERATED_RE.search(f):
                continue
            p = os.path.join(dirpath, f)
            try:
                if os.path.getsize(p) > MAX_FILE_BYTES:
                    continue
            except OSError:
                continue
            yield p


def lang_of(path):
    name = os.path.basename(path).lower()
    if name.endswith(".blade.php"):
        return "Blade"
    return LANG_BY_EXT.get(os.path.splitext(name)[1])


def read(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            return fh.read()
    except OSError:
        return ""


def is_test_file(rel):
    r = rel.lower()
    base = os.path.basename(r)
    return ("/tests/" in f"/{r}" or "/test/" in f"/{r}" or "__tests__" in r
            or base.startswith("test_") or base.endswith("_test.py")
            or ".test." in base or ".spec." in base or base.endswith("_test.go")
            or base.endswith("test.php"))


def git(root, *args):
    try:
        out = subprocess.run(["git", "-C", root, *args], capture_output=True,
                             text=True, timeout=120)
        return out.stdout if out.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired):
        return ""


def git_stats(root, author):
    if not os.path.isdir(os.path.join(root, ".git")):
        return {"available": False}
    shallow = git(root, "rev-parse", "--is-shallow-repository").strip() == "true"
    log = git(root, "log", "--no-merges", "--format=%H\t%an\t%ae\t%aI")
    rows = [l.split("\t") for l in log.splitlines() if l.count("\t") == 3]
    if not rows:
        return {"available": True, "commits": 0, "shallow": shallow}
    dates = sorted(r[3][:10] for r in rows)
    authors = Counter(f"{r[1]} <{r[2]}>" for r in rows)
    bot = re.compile(r"\[bot\]|github-actions|dependabot|renovate|pre-commit-ci", re.I)
    humans = Counter({k: v for k, v in authors.items() if not bot.search(k)})
    human_commits = sum(humans.values())
    months = Counter(r[3][:7] for r in rows)
    stats = {
        "available": True,
        "shallow_clone": shallow,
        "commits_non_merge": len(rows),
        "first_commit": dates[0],
        "last_commit": dates[-1],
        "active_months": len(months),
        "contributors_human": len(humans),
        "bot_commits": len(rows) - human_commits,
        "top_contributors": humans.most_common(8),
        "merged_prs_estimate": len(re.findall(r"Merge pull request|\(#\d+\)",
                                              git(root, "log", "--format=%s"))),
        "tags": len([t for t in git(root, "tag").splitlines() if t.strip()]),
    }
    if author:
        a = author.lower()
        mine = [r for r in rows if a in r[1].lower() or a in r[2].lower()]
        stats["author_filter"] = author
        stats["author_commits"] = len(mine)
        stats["author_commit_share_pct"] = round(100 * len(mine) / max(human_commits, 1), 1)
        if mine:
            numstat = git(root, "log", "--no-merges", f"--author={author}",
                          "--numstat", "--format=")
            add = rem = 0
            files_touched = set()
            dir_churn = Counter()
            for line in numstat.splitlines():
                parts = line.split("\t")
                if len(parts) == 3 and parts[0].isdigit() and parts[1].isdigit():
                    if any(s in parts[2] for s in SKIP_FILES):
                        continue
                    add += int(parts[0]); rem += int(parts[1]); files_touched.add(parts[2])
                    d = "/".join(parts[2].split("/")[:2]) if "/" in parts[2] else "(root)"
                    dir_churn[d] += int(parts[0]) + int(parts[1])
            stats["author_lines_added"] = add
            stats["author_lines_removed"] = rem
            stats["author_files_touched"] = len(files_touched)
            # where the author's work actually lives — use this to scope ownership claims
            stats["author_top_dirs_by_churn"] = dir_churn.most_common(8)
            stats["author_first_last"] = [min(r[3][:10] for r in mine),
                                          max(r[3][:10] for r in mine)]
    stats["commit_aspects"] = classify_commits(root, author)
    return stats


def classify_commits(root, author=None):
    """Bucket non-merge commit subjects (the author's, if given) by impact aspect."""
    args = ["log", "--no-merges", "--format=%h\t%ad\t%s", "--date=short"]
    if author:
        args.insert(2, f"--author={author}")
    rows = [l.split("\t", 2) for l in git(root, *args).splitlines() if l.count("\t") >= 2]
    out = {}
    for aspect, rx in COMMIT_ASPECTS_RE.items():
        hits = [r for r in rows if rx.search(r[2])]
        if hits:
            out[aspect] = {
                "count": len(hits),
                "span": [min(h[1] for h in hits), max(h[1] for h in hits)],
                "examples": [f"{h[0]} {h[1]} {h[2][:100]}" for h in hits[:MAX_COMMIT_EXAMPLES]],
            }
    return {"scope": f"author {author}" if author else "all authors",
            "commits_scanned": len(rows), "aspects": out}


def scan(root, author=None):
    loc = Counter()
    files_by_lang = Counter()
    test_files = 0
    test_loc = 0
    hits = {fam: defaultdict(lambda: {"count": 0, "examples": []}) for fam in PATTERNS}
    compiled = {fam: [(p[0], re.compile(p[1], re.M), p[2] if len(p) > 2 else None) for p in pats]
                for fam, pats in PATTERNS.items()}
    constants, claims = [], []
    infra = defaultdict(list)
    deps = {}
    llm_models = Counter()
    migrations = []
    config_signals = defaultdict(list)

    for path in iter_files(root):
        rel = os.path.relpath(path, root)
        base = os.path.basename(path)
        lang = lang_of(path)
        text = None

        # ---- infra & config files ----
        low = base.lower()
        if low.startswith("dockerfile") or low.endswith(".dockerfile"):
            text = read(path)
            stages = len(re.findall(r"^\s*FROM\s", text, re.M | re.I))
            infra["dockerfiles"].append(f"{rel} ({stages} stage{'s' if stages != 1 else ''})")
            if re.search(r"^\s*HEALTHCHECK\s", text, re.M):
                config_signals["health_probes"].append(rel)
        elif re.match(r"(docker-)?compose(\.\w+)?\.ya?ml$", low):
            text = read(path)
            m = re.search(r"^services:\s*\n((?:[ \t]+.*\n?|\s*\n)*)", text, re.M)
            svcs = re.findall(r"^  ([\w.-]+):\s*$", m.group(1), re.M) if m else []
            infra["compose_services"].append(f"{rel}: {', '.join(svcs) or '?'}")
        elif ".github/workflows" in rel.replace("\\", "/") and low.endswith((".yml", ".yaml")):
            text = read(path)
            jobs = re.findall(r"^  ([\w-]+):\s*$", text.split("jobs:", 1)[-1], re.M)
            infra["github_actions"].append(f"{rel} (jobs: {', '.join(jobs) or '?'})")
        elif low in {"cloudbuild.yaml", "cloudbuild.yml", "app.yaml", "service.yaml",
                     ".gitlab-ci.yml", "jenkinsfile", "vercel.json", "netlify.toml",
                     "fly.toml", "render.yaml", "procfile", "skaffold.yaml"}:
            infra["deploy_config"].append(rel)
        elif low.endswith(".tf"):
            infra["terraform"].append(rel)
        elif low.endswith((".yaml", ".yml")) and "kind: Deployment" in (text := read(path)):
            infra["kubernetes"].append(rel)
        if low in {"makefile", "justfile"}:
            infra["task_runner"].append(rel)

        # ---- deploy/config signals (scale-to-zero, probes, secret scanning, CI cache…) ----
        if low.endswith(CONFIG_EXTS) or low in {".pre-commit-config.yaml", "jenkinsfile"}:
            ctext = text if text is not None else read(path)
            for sig, rx in CONFIG_SIGNALS_RE.items():
                mm = rx.search(ctext)
                if mm and len(config_signals[sig]) < 8:
                    config_signals[sig].append(f"{rel}:{ctext.count(chr(10), 0, mm.start()) + 1}")

        # ---- DB schema migrations ----
        rel_posix = rel.replace("\\", "/")
        if MIGRATION_PATH_RE.search(rel_posix) and (lang in CODE_LANGS or lang in SCHEMA_LANGS) \
                and not base.startswith("__init__"):
            migrations.append(rel_posix)

        # ---- dependency manifests ----
        if low == "package.json" and "node_modules" not in rel:
            try:
                pj = json.loads(read(path))
                deps[rel] = {"dependencies": sorted(pj.get("dependencies", {})),
                             "devDependencies": sorted(pj.get("devDependencies", {})),
                             "scripts": pj.get("scripts", {})}
            except ValueError:
                pass
        elif low.startswith("requirements") and low.endswith(".txt"):
            deps[rel] = sorted({re.split(r"[<>=~!\[; ]", l.strip())[0]
                                for l in read(path).splitlines()
                                if l.strip() and not l.startswith(("#", "-"))})
        elif low == "pyproject.toml":
            names = set()
            try:
                import tomllib
                t = tomllib.loads(read(path))
                raw = list(t.get("project", {}).get("dependencies", []))
                for grp in t.get("dependency-groups", {}).values():
                    raw += [x for x in grp if isinstance(x, str)]
                for grp in t.get("project", {}).get("optional-dependencies", {}).values():
                    raw += grp
                raw += list(t.get("tool", {}).get("poetry", {}).get("dependencies", {}))
                names = {re.split(r"[<>=~!\[; ]", d.strip())[0] for d in raw if d.strip()}
            except Exception:
                names = set(re.findall(r'^\s*"([A-Za-z0-9_.\-]+)', read(path), re.M))
            if names:
                deps[rel] = sorted(n for n in names if n and n.lower() != "python")
        elif low == "composer.json":
            try:
                cj = json.loads(read(path))
                deps[rel] = sorted(list(cj.get("require", {})) + list(cj.get("require-dev", {})))
            except ValueError:
                pass

        # ---- README claims ----
        if low.startswith("readme") and low.endswith((".md", ".rst", ".txt")):
            for i, line in enumerate(read(path).splitlines(), 1):
                if CLAIM_RE.search(line) and len(claims) < 40 and not line.strip().startswith(("![", "[![", "<img")):
                    claims.append(f"{rel}:{i}: {line.strip()[:160]}")

        if not lang:
            continue
        text = text if text is not None else read(path)
        n = sum(1 for l in text.splitlines() if l.strip())
        loc[lang] += n
        files_by_lang[lang] += 1
        testy = is_test_file(rel)
        if testy:
            test_files += 1
            test_loc += n
        if lang not in CODE_LANGS and lang not in SCHEMA_LANGS:
            continue

        for fam, pats in compiled.items():
            if fam == "tests" and not testy:
                continue
            if fam != "tests" and testy:
                continue
            for label, rx, langs in pats:
                if langs and lang not in langs:
                    continue
                if label == "Django path" and not base.startswith("urls"):
                    continue
                ms = list(rx.finditer(text))
                if not ms:
                    continue
                h = hits[fam][label]
                h["count"] += len(ms)
                for mm in ms[:2]:
                    ln = text.count("\n", 0, mm.start()) + 1
                    ref = f"{rel}:{ln}"
                    if len(h["examples"]) < 4 and ref not in h["examples"]:
                        h["examples"].append(ref)
                if label == "LLM model id":
                    for mm in ms:
                        llm_models[mm.group(1)] += 1

        if not testy:
            for mm in CONSTANT_RE.finditer(text):
                if len(constants) < 40:
                    ln = text.count("\n", 0, mm.start()) + 1
                    constants.append(f"{rel}:{ln}: {mm.group(1)} = {mm.group(2)}")

    code_loc = sum(v for k, v in loc.items() if k in CODE_LANGS)
    return {
        "repo": os.path.abspath(root),
        "scanned_at": datetime.now().isoformat(timespec="seconds"),
        "loc_non_blank_by_language": loc.most_common(),
        "files_by_language": files_by_lang.most_common(),
        "code_loc_total": code_loc,
        "test_files": test_files,
        "test_loc": test_loc,
        "test_to_code_loc_ratio": round(test_loc / code_loc, 2) if code_loc else None,
        "patterns": {fam: {k: v for k, v in d.items()} for fam, d in hits.items()},
        "llm_models_referenced": llm_models.most_common(),
        "infra": dict(infra),
        "dependencies": deps,
        "design_constants": constants,
        "readme_numeric_claims": claims,
        "db_migrations": {"count": len(migrations), "examples": sorted(migrations)[:3] + sorted(migrations)[-3:]
                          if len(migrations) > 6 else sorted(migrations)},
        "config_signals": dict(config_signals),
        "git": git_stats(root, author),
    }


def to_markdown(r):
    out = [f"# Evidence ledger — {os.path.basename(r['repo'])}",
           f"_scanned {r['scanned_at']}; counts are pattern-based heuristics — verify before citing_\n"]
    g = r["git"]
    out.append("## Git history")
    if not g.get("available"):
        out.append("- No .git directory: ownership and timeline cannot be verified from history.")
    elif not g.get("commits_non_merge"):
        out.append("- Git repo has no commits (or history unavailable).")
    else:
        if g.get("shallow_clone"):
            out.append("- ⚠️ Shallow clone — history is truncated; re-clone without --depth for real numbers.")
        out.append(f"- {g['commits_non_merge']} non-merge commits, {g['first_commit']} → {g['last_commit']}, "
                   f"{g['active_months']} active months, {g['contributors_human']} human contributors "
                   f"(+{g['bot_commits']} bot commits excluded from shares), "
                   f"{g['tags']} tags, ~{g['merged_prs_estimate']} merged PR references")
        out.append("- Top contributors: " + "; ".join(f"{a} ({c})" for a, c in g["top_contributors"]))
        if "author_commits" in g:
            out.append(f"- **Author `{g['author_filter']}`**: {g['author_commits']} commits "
                       f"({g['author_commit_share_pct']}% of human commits)"
                       + (f", +{g['author_lines_added']}/−{g['author_lines_removed']} lines, "
                          f"{g['author_files_touched']} files, {g['author_first_last'][0]} → {g['author_first_last'][1]}"
                          if g.get("author_commits") else " — author string matched nothing; check `git shortlog -sne`"))
            if g.get("author_top_dirs_by_churn"):
                out.append("- Author's work concentrates in: " + ", ".join(
                    f"{d} ({c} lines churn)" for d, c in g["author_top_dirs_by_churn"]))
    out.append("\n## Size & stack")
    out.append(f"- Code LOC (non-blank, excl. vendored/lockfiles): {r['code_loc_total']}")
    out.append("- By language: " + ", ".join(f"{k} {v}" for k, v in r["loc_non_blank_by_language"][:10]))
    out.append(f"- Test files: {r['test_files']} ({r['test_loc']} LOC; test:code ratio {r['test_to_code_loc_ratio']})")
    for fam, d in r["patterns"].items():
        if not d:
            continue
        out.append(f"\n## {fam.replace('_', ' ').title()}")
        for label, v in sorted(d.items(), key=lambda kv: -kv[1]["count"]):
            out.append(f"- {label}: {v['count']}  ← {', '.join(v['examples'])}")
    if r["llm_models_referenced"]:
        out.append("\n## LLM models referenced")
        out.append("- " + ", ".join(f"{m} ({c})" for m, c in r["llm_models_referenced"]))
    if r["infra"]:
        out.append("\n## Infra / delivery")
        for k, v in r["infra"].items():
            out.append(f"- {k}: " + "; ".join(v[:8]) + (f" (+{len(v)-8} more)" if len(v) > 8 else ""))
    if r["dependencies"]:
        out.append("\n## Dependency manifests")
        for k, v in r["dependencies"].items():
            if isinstance(v, dict):
                out.append(f"- {k}: deps={', '.join(v['dependencies'][:25])}"
                           f" | dev={', '.join(v['devDependencies'][:15])}"
                           f" | scripts={', '.join(v['scripts'])}")
            else:
                out.append(f"- {k}: {', '.join(v[:30])}")
    if r["design_constants"]:
        out.append("\n## Design constants (thresholds/limits worth citing)")
        out.extend(f"- {c}" for c in r["design_constants"])
    if r["db_migrations"]["count"]:
        out.append("\n## DB schema migrations")
        out.append(f"- {r['db_migrations']['count']} migration files ← "
                   + ", ".join(r["db_migrations"]["examples"]))
        out.append("- Index/constraint migrations appear under Performance above; "
                   "`git log --format='%ad %an' -- <file>` dates and attributes each one")
    if r["config_signals"]:
        out.append("\n## Deploy & config signals (rung 2 — the outcome number lives outside the repo)")
        for k, v in r["config_signals"].items():
            out.append(f"- {k.replace('_', ' ')}: {', '.join(v)}")
    ca = g.get("commit_aspects") if g.get("available") else None
    if ca and ca["aspects"]:
        out.append(f"\n## Commit subjects by aspect ({ca['scope']}, {ca['commits_scanned']} commits) "
                   "— memory aid; read each diff before claiming")
        for aspect, v in sorted(ca["aspects"].items(), key=lambda kv: -kv[1]["count"]):
            out.append(f"- **{aspect.replace('_', ' ')}**: {v['count']} commits, {v['span'][0]} → {v['span'][1]}")
            out.extend(f"  - {e}" for e in v["examples"])
    if r["readme_numeric_claims"]:
        out.append("\n## Numeric claims in README (UNVERIFIED — check each against code/runs)")
        out.extend(f"- {c}" for c in r["readme_numeric_claims"])
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("repo", help="path to a local checkout")
    ap.add_argument("--author", help="substring of the user's git name or email, for ownership stats")
    ap.add_argument("--json", help="also write the full ledger as JSON to this path")
    a = ap.parse_args()
    if not os.path.isdir(a.repo):
        sys.exit(f"not a directory: {a.repo}")
    r = scan(a.repo, a.author)
    if a.json:
        with open(a.json, "w") as fh:
            json.dump(r, fh, indent=2, default=list)
    print(to_markdown(r))


if __name__ == "__main__":
    main()
