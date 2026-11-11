"""Tests for scripts/repo_metrics.py. Stdlib only: python3 -m unittest discover tests"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "repo_metrics.py")

spec = importlib.util.spec_from_file_location("repo_metrics", SCRIPT)
rm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rm)

GIT_ID = ["-c", "user.name=Test Author", "-c", "user.email=author@example.com",
          "-c", "commit.gpgsign=false"]
OTHER_ID = ["-c", "user.name=Someone Else", "-c", "user.email=other@example.com",
            "-c", "commit.gpgsign=false"]

FILES = {
    "database/migrations/2024_01_01_add_tx_index.php":
        "<?php Schema::table('tx', function ($t) { $t->index('user_id'); });\n",
    "app/Http/TxController.php": textwrap.dedent("""\
        <?php
        class TxController {
          public function index() { $this->authorize('view', Tx::class); return Tx::with('user')->paginate(20); }
          public function pay() { Gate::allows('pay'); $m = new \\Midtrans\\Snap(); Http::post('https://api.xendit.co'); }
        }
        Route::get('/tx', [TxController::class, 'index'])->middleware(['can:view']);
        """),
    "prisma/schema.prisma": "model Lead {\n  id Int @id\n  formId String\n  @@index([formId])\n}\n",
    "src/leads.ts": textwrap.dedent("""\
        import twilio from 'twilio';
        const leads = await prisma.lead.findMany({ include: { form: true }, skip: page, take: 20 });
        fetch('https://graph.facebook.com/v19.0/leadgen');
        """),
    "deploy/service.yaml": textwrap.dedent("""\
        spec:
          template:
            metadata:
              annotations:
                autoscaling.knative.dev/minScale: "0"
            spec:
              containers:
                - readinessProbe: {}
        """),
    "docker-compose.yml": "services:\n  api:\n    healthcheck:\n      test: [\"CMD\", \"true\"]\n",
    ".pre-commit-config.yaml": "repos:\n  - repo: https://github.com/gitleaks/gitleaks\n",
    ".github/workflows/ci.yml": "jobs:\n  test:\n    steps:\n      - uses: actions/cache@v4\n",
    "deploy/nginx.conf": "limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;\n",
    "Dockerfile": "FROM node:20 AS build\nFROM node:20-slim\nHEALTHCHECK CMD true\n",
    "tests/test_tx.py": "def test_tx():\n    assert True\n",
    # vendored code must never be attributed to the author
    "node_modules/pkg/index.js": "require('midtrans'); require('stripe');\n",
    "package-lock.json": "{\"stripe\": \"1.0.0\"}\n",
}

AUTHOR_COMMITS = [
    "perf: add index on tx.user_id to fix slow listing",
    "refactor: migrate leads from MongoDB to PostgreSQL with backfill",
    "fix: idempotent webhook retry with dedup",
    "feat: RBAC permission middleware",
    "ci: add GitHub Actions pipeline with cache",
    "chore: scale-to-zero min-instances on Cloud Run to cut cost",
    "test: raise coverage for payment module",
]


def git(repo, *args, ident=GIT_ID):
    subprocess.run(["git", *ident, "-C", repo, *args], check=True,
                   capture_output=True, text=True)


def build_fixture(path):
    for rel, content in FILES.items():
        full = os.path.join(path, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w") as fh:
            fh.write(content)
    git(path, "init", "-q")
    git(path, "add", "-A")
    git(path, "commit", "-qm", "feat: initial api")
    for msg in AUTHOR_COMMITS:
        git(path, "commit", "-q", "--allow-empty", "-m", msg)
    git(path, "commit", "-q", "--allow-empty", "-m", "perf: optimize cache warmup", ident=OTHER_ID)


@unittest.skipUnless(shutil.which("git"), "git is required")
class RepoMetricsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        build_fixture(cls.tmp)
        cls.r = rm.scan(cls.tmp, author="author@example.com")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def labels(self, family):
        return {k: v["count"] for k, v in self.r["patterns"][family].items()}

    def test_performance_mechanisms(self):
        perf = self.labels("performance")
        self.assertEqual(perf.get("Index in migration/schema"), 2)   # PHP migration + Prisma
        self.assertEqual(perf.get("Eager loading (N+1 guard)"), 2)   # Laravel with() + Prisma include
        self.assertEqual(perf.get("Pagination"), 2)                  # Laravel ->paginate( + Prisma take:

    def test_authorization(self):
        self.assertGreaterEqual(self.labels("security").get("Authorization (RBAC / policy)", 0), 3)

    def test_third_party_integrations(self):
        found = set(self.labels("third_party_integrations"))
        self.assertTrue({"Midtrans", "Xendit", "Twilio", "Meta / Facebook Graph"} <= found)

    def test_vendored_and_lockfiles_are_ignored(self):
        self.assertNotIn("Stripe", self.labels("third_party_integrations"))
        midtrans = self.r["patterns"]["third_party_integrations"]["Midtrans"]
        self.assertTrue(all("node_modules" not in e for e in midtrans["examples"]))

    def test_prisma_files_are_scanned(self):
        self.assertEqual(self.labels("data_models").get("Prisma model"), 1)

    def test_db_migrations(self):
        self.assertEqual(self.r["db_migrations"]["count"], 1)

    def test_config_signals(self):
        sig = self.r["config_signals"]
        for key in ("scale_to_zero", "health_probes", "secret_scanning", "ci_caching", "rate_limit_config"):
            self.assertIn(key, sig, key)
        self.assertIn("Dockerfile", sig["health_probes"])

    def test_tests_are_counted_separately(self):
        self.assertEqual(self.r["test_files"], 1)
        self.assertEqual(self.labels("tests").get("pytest test fn"), 1)

    def test_author_ownership(self):
        g = self.r["git"]
        self.assertEqual(g["author_commits"], 8)                    # initial + 7
        self.assertEqual(g["commits_non_merge"], 9)
        self.assertEqual(g["author_commit_share_pct"], round(100 * 8 / 9, 1))

    def test_commit_aspects(self):
        ca = self.r["git"]["commit_aspects"]
        self.assertEqual(ca["scope"], "author author@example.com")
        aspects = ca["aspects"]
        for key in ("performance", "architecture_migration", "reliability", "security",
                    "delivery_ci", "cost", "testing"):
            self.assertIn(key, aspects, key)
        perf_subjects = " ".join(aspects["performance"]["examples"])
        self.assertNotIn("pipeline with cache", perf_subjects)       # CI cache is not perf work
        self.assertNotIn("cache warmup", perf_subjects)              # other author's commit

    def test_commit_aspects_without_author_cover_everyone(self):
        ca = rm.classify_commits(self.tmp)
        self.assertEqual(ca["commits_scanned"], 9)
        self.assertEqual(ca["aspects"]["performance"]["count"], 2)

    def test_markdown_has_new_sections(self):
        md = rm.to_markdown(self.r)
        for heading in ("## Performance", "## Third Party Integrations", "## DB schema migrations",
                        "## Deploy & config signals", "## Commit subjects by aspect"):
            self.assertIn(heading, md)

    def test_cli_writes_valid_json(self):
        out = os.path.join(self.tmp, "..", "ledger-test.json")
        try:
            res = subprocess.run([sys.executable, "-I", SCRIPT, self.tmp, "--json", out],
                                 capture_output=True, text=True, check=True)
            self.assertIn("# Evidence ledger", res.stdout)
            with open(out) as fh:
                self.assertIn("patterns", json.load(fh))
        finally:
            if os.path.exists(out):
                os.remove(out)


class NoGitTest(unittest.TestCase):
    def test_directory_without_git(self):
        tmp = tempfile.mkdtemp()
        try:
            with open(os.path.join(tmp, "app.py"), "w") as fh:
                fh.write("import redis\n")
            r = rm.scan(tmp)
            self.assertFalse(r["git"]["available"])
            self.assertIn("No .git directory", rm.to_markdown(r))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
