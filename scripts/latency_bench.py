#!/usr/bin/env python3
"""
latency_bench.py — measure p50/p95/p99 latency and throughput of an HTTP
endpoint on a service YOU run (localhost, staging you own). Stdlib only, so
the user can run it on their laptop without installing anything.

Only point this at infrastructure the user owns. It is a measurement tool for
producing reproducible resume numbers, not a load-testing weapon: defaults are
gentle and --requests is capped.

Usage:
    python3 latency_bench.py http://localhost:8000/health -n 200 -c 10
    python3 latency_bench.py http://localhost:8000/invoices -X POST \
        -d @sample.json -H "Content-Type: application/json" -n 100 -c 5 --warmup 10

Compare two builds (e.g. before/after caching) by running it twice with the
same flags and reporting both numbers plus the delta.
"""
import argparse
import concurrent.futures as cf
import statistics
import time
import urllib.error
import urllib.request

MAX_REQUESTS = 5000


def one(url, method, body, headers, timeout):
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            r.read()
            code = r.status
    except urllib.error.HTTPError as e:
        code = e.code
    except Exception:
        code = -1
    return (time.perf_counter() - t0) * 1000, code


def pct(sorted_vals, p):
    if not sorted_vals:
        return float("nan")
    k = (len(sorted_vals) - 1) * p / 100
    f, c = int(k), min(int(k) + 1, len(sorted_vals) - 1)
    return sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url")
    ap.add_argument("-n", "--requests", type=int, default=200)
    ap.add_argument("-c", "--concurrency", type=int, default=10)
    ap.add_argument("-X", "--method", default="GET")
    ap.add_argument("-d", "--data", help="request body, or @file to read it from a file")
    ap.add_argument("-H", "--header", action="append", default=[], help="'Name: value' (repeatable)")
    ap.add_argument("--warmup", type=int, default=5, help="requests to discard first (JIT, pools, caches)")
    ap.add_argument("--timeout", type=float, default=30)
    a = ap.parse_args()

    n = min(a.requests, MAX_REQUESTS)
    body = None
    if a.data:
        body = open(a.data[1:], "rb").read() if a.data.startswith("@") else a.data.encode()
    headers = dict(h.split(":", 1) for h in a.header)
    headers = {k.strip(): v.strip() for k, v in headers.items()}

    for _ in range(a.warmup):
        one(a.url, a.method, body, headers, a.timeout)

    t0 = time.perf_counter()
    with cf.ThreadPoolExecutor(max_workers=a.concurrency) as ex:
        results = list(ex.map(lambda _: one(a.url, a.method, body, headers, a.timeout), range(n)))
    wall = time.perf_counter() - t0

    ok = sorted(ms for ms, code in results if 200 <= code < 400)
    errors = len(results) - len(ok)
    print(f"target        {a.method} {a.url}")
    print(f"requests      {n} (concurrency {a.concurrency}, warmup {a.warmup} discarded)")
    print(f"success       {len(ok)}  errors {errors} ({100 * errors / n:.1f}%)")
    if ok:
        print(f"latency ms    p50 {pct(ok, 50):.1f} | p95 {pct(ok, 95):.1f} | p99 {pct(ok, 99):.1f} "
              f"| mean {statistics.mean(ok):.1f} | max {ok[-1]:.1f}")
    print(f"throughput    {n / wall:.1f} req/s over {wall:.2f}s wall time")
    print("\nRecord alongside the number: machine/instance type, dataset size, commit SHA, and these flags.")


if __name__ == "__main__":
    main()
