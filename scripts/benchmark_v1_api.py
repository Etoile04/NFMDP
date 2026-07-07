"""P95 Performance Benchmark for NFM v1 API endpoints.

Runs load tests against /api/v1/materials, /api/v1/properties,
/api/v1/sources and computes P95 response times.

Usage:
    python scripts/benchmark_v1_api.py [--base-url URL] [--requests N] [--concurrency C]

Output:
    - Console summary table
    - JSON report file (benchmark_report.json)

Exit code:
    0 — all endpoints meet P95 < 500ms target
    1 — one or more endpoints exceed P95 target
"""

from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_BASE_URL = os.getenv(
    "NFM_API_BASE",
    "http://localhost:8000",
).rstrip("/")

P95_TARGET_MS = 500.0

DEFAULT_REQUESTS_PER_ENDPOINT = 50
DEFAULT_CONCURRENCY = 5
WARMUP_REQUESTS = 3


# ---------------------------------------------------------------------------
# Data Classes (immutable)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RequestResult:
    """Immutable record of a single HTTP request."""

    endpoint: str
    status_code: int
    response_time_ms: float
    success: bool
    error: str | None = None


@dataclass(frozen=True)
class EndpointStats:
    """Immutable aggregate statistics for one endpoint."""

    endpoint: str
    total_requests: int
    successful: int
    failed: int
    min_ms: float
    max_ms: float
    mean_ms: float
    median_ms: float
    p95_ms: float
    p99_ms: float
    stddev_ms: float
    passes_target: bool


@dataclass(frozen=True)
class BenchmarkReport:
    """Immutable benchmark report for all endpoints."""

    base_url: str
    total_requests: int
    concurrency: int
    endpoints: tuple[EndpointStats, ...]
    overall_passes: bool
    timestamp: str


# ---------------------------------------------------------------------------
# HTTP Client
# ---------------------------------------------------------------------------


def make_request(base_url: str, path: str) -> RequestResult:
    """Send a single GET request and return timing result."""
    url = base_url + path
    req = Request(url, method="GET")
    start = time.monotonic()
    try:
        with urlopen(req, timeout=30) as resp:
            elapsed_ms = (time.monotonic() - start) * 1000
            return RequestResult(
                endpoint=path,
                status_code=resp.status,
                response_time_ms=elapsed_ms,
                success=True,
            )
    except HTTPError as exc:
        elapsed_ms = (time.monotonic() - start) * 1000
        return RequestResult(
            endpoint=path,
            status_code=exc.code,
            response_time_ms=elapsed_ms,
            success=False,
            error=f"HTTP {exc.code}",
        )
    except URLError as exc:
        elapsed_ms = (time.monotonic() - start) * 1000
        return RequestResult(
            endpoint=path,
            status_code=0,
            response_time_ms=elapsed_ms,
            success=False,
            error=str(exc.reason),
        )


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------


def compute_percentile(sorted_data: list[float], percentile: float) -> float:
    """Compute percentile from sorted data using nearest-rank method."""
    if not sorted_data:
        return 0.0
    k = (percentile / 100.0) * (len(sorted_data) - 1)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_data[int(k)]
    d0 = sorted_data[int(f)] * (c - k)
    d1 = sorted_data[int(c)] * (k - f)
    return d0 + d1


def compute_stats(
    endpoint: str,
    results: list[RequestResult],
    target_ms: float,
) -> EndpointStats:
    """Compute aggregate statistics from request results."""
    successful_results = [r for r in results if r.success]
    failed_count = len(results) - len(successful_results)
    latencies = sorted(r.response_time_ms for r in successful_results)

    if not latencies:
        return EndpointStats(
            endpoint=endpoint,
            total_requests=len(results),
            successful=0,
            failed=failed_count,
            min_ms=0.0,
            max_ms=0.0,
            mean_ms=0.0,
            median_ms=0.0,
            p95_ms=float("inf"),
            p99_ms=float("inf"),
            stddev_ms=0.0,
            passes_target=False,
        )

    mean_val = statistics.mean(latencies)
    p95_val = compute_percentile(latencies, 95)
    p99_val = compute_percentile(latencies, 99)

    stddev_val = (
        statistics.stdev(latencies) if len(latencies) > 1 else 0.0
    )

    return EndpointStats(
        endpoint=endpoint,
        total_requests=len(results),
        successful=len(successful_results),
        failed=failed_count,
        min_ms=latencies[0],
        max_ms=latencies[-1],
        mean_ms=round(mean_val, 2),
        median_ms=round(statistics.median(latencies), 2),
        p95_ms=round(p95_val, 2),
        p99_ms=round(p99_val, 2),
        stddev_ms=round(stddev_val, 2),
        passes_target=p95_val < target_ms,
    )


# ---------------------------------------------------------------------------
# Benchmark Runner
# ---------------------------------------------------------------------------


ENDPOINTS = [
    "/health",
    "/api/v1/materials",
    "/api/v1/materials?limit=5",
    "/api/v1/sources",
    "/api/v1/sources?limit=5",
    "/api/v1/properties",
    "/api/v1/properties?limit=5",
]


def warmup(base_url: str) -> bool:
    """Send warmup requests to establish connection pools."""
    print(f"Warming up against {base_url} ...")
    for endpoint in ENDPOINTS:
        result = make_request(base_url, endpoint)
        if not result.success:
            print(f"  WARN: {endpoint} returned {result.error}")
    print("Warmup complete.")
    return True


def run_benchmark(
    base_url: str,
    requests_per_endpoint: int,
    concurrency: int,
) -> list[RequestResult]:
    """Run benchmark across all endpoints with given concurrency."""
    all_results: list[RequestResult] = []

    for endpoint in ENDPOINTS:
        print(
            f"  Benchmarking {endpoint} "
            f"({requests_per_endpoint} requests, {concurrency} concurrent)...",
            end="",
            flush=True,
        )

        results: list[RequestResult] = []

        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [
                executor.submit(make_request, base_url, endpoint)
                for _ in range(requests_per_endpoint)
            ]
            for future in as_completed(futures):
                results.append(future.result())

        all_results.extend(results)
        successful = sum(1 for r in results if r.success)
        print(f" {successful}/{len(results)} OK")

    return all_results


def format_report(report: BenchmarkReport) -> str:
    """Format benchmark report as human-readable table."""
    lines = [
        "",
        "=" * 72,
        "  NFM V1 API Performance Benchmark Report",
        "=" * 72,
        f"  Base URL:    {report.base_url}",
        f"  Timestamp:   {report.timestamp}",
        f"  Concurrency:  {report.concurrency}",
        f"  Total reqs:   {report.total_requests}",
        f"  P95 Target:   < {P95_TARGET_MS:.0f}ms",
        "-" * 72,
        "",
        f"  {'Endpoint':<40} {'P95 (ms)':>9} {'Mean (ms)':>10} {'Pass':>6}",
        f"  {'-'*40} {'-'*9} {'-'*10} {'-'*6}",
    ]

    for stats in report.endpoints:
        status = "PASS" if stats.passes_target else "FAIL"
        lines.append(
            f"  {stats.endpoint:<40} {stats.p95_ms:>9.2f} "
            f"{stats.mean_ms:>10.2f} {status:>6}"
        )

    lines.extend([
        "",
        "-" * 72,
        f"  Overall: {'ALL PASS' if report.overall_passes else 'FAILURES DETECTED'}",
        "=" * 72,
        "",
    ])

    return "\n".join(lines)


def generate_json_report(report: BenchmarkReport) -> dict[str, Any]:
    """Convert report to JSON-serializable dict."""
    return {
        "base_url": report.base_url,
        "timestamp": report.timestamp,
        "concurrency": report.concurrency,
        "p95_target_ms": P95_TARGET_MS,
        "overall_passes": report.overall_passes,
        "endpoints": [
            {
                "endpoint": s.endpoint,
                "total_requests": s.total_requests,
                "successful": s.successful,
                "failed": s.failed,
                "min_ms": s.min_ms,
                "max_ms": s.max_ms,
                "mean_ms": s.mean_ms,
                "median_ms": s.median_ms,
                "p95_ms": s.p95_ms,
                "p99_ms": s.p99_ms,
                "stddev_ms": s.stddev_ms,
                "passes_target": s.passes_target,
            }
            for s in report.endpoints
        ],
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="P95 Performance Benchmark for NFM v1 API",
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"API base URL (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--requests",
        type=int,
        default=DEFAULT_REQUESTS_PER_ENDPOINT,
        help=f"Requests per endpoint (default: {DEFAULT_REQUESTS_PER_ENDPOINT})",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=DEFAULT_CONCURRENCY,
        help=f"Concurrent requests (default: {DEFAULT_CONCURRENCY})",
    )
    parser.add_argument(
        "--output",
        default="benchmark_report.json",
        help="Output JSON report path (default: benchmark_report.json)",
    )
    parser.add_argument(
        "--target-ms",
        type=float,
        default=P95_TARGET_MS,
        help=f"P95 target in ms (default: {P95_TARGET_MS})",
    )
    args = parser.parse_args(argv)

    # Warmup
    if not warmup(args.base_url):
        print("ERROR: Warmup failed — API not reachable")
        return 1

    # Run benchmark
    print(
        f"\nRunning benchmark: {args.requests} req/endpoint, "
        f"concurrency={args.concurrency}"
    )
    all_results = run_benchmark(
        args.base_url, args.requests, args.concurrency,
    )

    # Compute per-endpoint stats
    endpoint_results: dict[str, list[RequestResult]] = {}
    for result in all_results:
        endpoint_results.setdefault(result.endpoint, []).append(result)

    endpoint_stats_list: list[EndpointStats] = []
    for endpoint, results in endpoint_results.items():
        stats = compute_stats(endpoint, results, args.target_ms)
        endpoint_stats_list.append(stats)

    # Sort by endpoint path for consistent output
    endpoint_stats_list.sort(key=lambda s: s.endpoint)

    overall_passes = all(s.passes_target for s in endpoint_stats_list)

    report = BenchmarkReport(
        base_url=args.base_url,
        total_requests=len(all_results),
        concurrency=args.concurrency,
        endpoints=tuple(endpoint_stats_list),
        overall_passes=overall_passes,
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    )

    # Console output
    print(format_report(report))

    # JSON output
    json_data = generate_json_report(report)
    output_path = args.output
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    print(f"JSON report written to: {output_path}")

    return 0 if overall_passes else 1


if __name__ == "__main__":
    sys.exit(main())
