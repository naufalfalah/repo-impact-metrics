"""Tests for scripts/latency_bench.py. Stdlib only: python3 -m unittest discover tests"""
import http.server
import importlib.util
import os
import subprocess
import sys
import threading
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "latency_bench.py")

spec = importlib.util.spec_from_file_location("latency_bench", SCRIPT)
lb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lb)


class PercentileTest(unittest.TestCase):
    def test_interpolates(self):
        vals = [10.0, 20.0, 30.0, 40.0, 50.0]
        self.assertEqual(lb.pct(vals, 0), 10.0)
        self.assertEqual(lb.pct(vals, 50), 30.0)
        self.assertEqual(lb.pct(vals, 100), 50.0)
        self.assertAlmostEqual(lb.pct(vals, 95), 48.0)

    def test_empty_is_nan(self):
        v = lb.pct([], 95)
        self.assertNotEqual(v, v)


class _Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        code = 500 if self.path == "/fail" else 200
        self.send_response(code)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *args):
        pass


class LocalServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        cls.base = f"http://127.0.0.1:{cls.srv.server_address[1]}"
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def run_bench(self, path):
        return subprocess.run([sys.executable, "-I", SCRIPT, self.base + path,
                               "-n", "20", "-c", "2", "--warmup", "1"],
                              capture_output=True, text=True, check=True, timeout=60).stdout

    def test_successful_requests(self):
        out = self.run_bench("/health")
        self.assertIn("success       20  errors 0 (0.0%)", out)
        self.assertIn("latency ms    p50", out)

    def test_server_errors_are_counted(self):
        out = self.run_bench("/fail")
        self.assertIn("success       0  errors 20 (100.0%)", out)
        self.assertNotIn("latency ms", out)


if __name__ == "__main__":
    unittest.main()
