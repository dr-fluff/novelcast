#!/usr/bin/env python3
"""Measure page response time and optional server resource usage.

Examples:
    python scripts/benchmark_pages.py --base-url http://localhost:8001
    python scripts/benchmark_pages.py --base-url http://localhost:8001 \
        --url /story?story_id=1 --cookie 'session=...' --pid 12345 --repeat 5
"""

from __future__ import annotations

import argparse
import statistics
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from threading import Event, Thread


@dataclass
class Sample:
    status: int
    final_url: str
    first_byte_ms: float
    total_ms: float
    bytes_received: int


@dataclass
class ResourceSample:
    cpu_percent: float
    rss_mb: float


def read_process_usage(pid: int) -> ResourceSample | None:
    try:
        result = subprocess.run(
            ["ps", "-p", str(pid), "-o", "%cpu=,rss="],
            check=True,
            capture_output=True,
            text=True,
        )
        cpu, rss_kb = result.stdout.strip().split()
        return ResourceSample(float(cpu), float(rss_kb) / 1024)
    except (OSError, ValueError, subprocess.CalledProcessError):
        return None


def sample_process(pid: int, stop: Event, samples: list[ResourceSample], interval: float) -> None:
    while not stop.is_set():
        usage = read_process_usage(pid)
        if usage:
            samples.append(usage)
        stop.wait(interval)


def measure(url: str, cookie: str | None, timeout: float) -> Sample:
    request = urllib.request.Request(url, headers={"User-Agent": "NovelCast page benchmark"})
    if cookie:
        request.add_header("Cookie", cookie)

    started = time.perf_counter()
    first_byte = None
    status = 0
    final_url = url
    bytes_received = 0
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = response.status
            final_url = response.geturl()
            chunks = []
            while True:
                chunk = response.read(64 * 1024)
                if not chunk:
                    break
                if first_byte is None:
                    first_byte = time.perf_counter()
                chunks.append(chunk)
            bytes_received = sum(map(len, chunks))
    except urllib.error.HTTPError as error:
        status = error.code
        final_url = error.geturl()
        error.read()
    except (urllib.error.URLError, ConnectionResetError, TimeoutError) as error:
        reason = getattr(error, "reason", str(error))
        raise RuntimeError(f"{url}: {reason}") from error

    finished = time.perf_counter()
    first_byte = first_byte or finished
    return Sample(
        status=status,
        final_url=final_url,
        first_byte_ms=(first_byte - started) * 1000,
        total_ms=(finished - started) * 1000,
        bytes_received=bytes_received,
    )


def summarize(path: str, samples: list[Sample]) -> None:
    totals = [sample.total_ms for sample in samples]
    first_bytes = [sample.first_byte_ms for sample in samples]
    sizes = [sample.bytes_received for sample in samples]
    status = samples[-1].status
    final_url = samples[-1].final_url
    destination = f" -> {final_url}" if final_url != path else ""
    print(
        f"{path:<42} {status:>3}  "
        f"TTFB avg {statistics.mean(first_bytes):>8.1f} ms  "
        f"total avg {statistics.mean(totals):>8.1f} ms  "
        f"min/max {min(totals):.1f}/{max(totals):.1f} ms  "
        f"size {statistics.mean(sizes) / 1024:>8.1f} KB{destination}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:8001")
    parser.add_argument(
        "--url",
        dest="urls",
        action="append",
        help="Path to measure. Repeat the option; defaults to common public pages.",
    )
    parser.add_argument(
        "--story-id",
        dest="story_ids",
        action="append",
        type=int,
        help="Story ID to benchmark. Repeat the option for multiple stories.",
    )
    parser.add_argument("--cookie", help="Cookie header for authenticated pages, e.g. 'session=...'")
    parser.add_argument("--pid", type=int, help="Server PID to sample for CPU and RSS usage")
    parser.add_argument("--repeat", type=int, default=3, help="Requests per page (default: 3)")
    parser.add_argument("--timeout", type=float, default=30, help="Request timeout in seconds")
    args = parser.parse_args()

    if args.repeat < 1:
        parser.error("--repeat must be at least 1")

    paths = args.urls or ["/", "/authors", "/search", "/settings"]
    paths += [f"/story?story_id={story_id}" for story_id in args.story_ids or []]
    base_url = args.base_url.rstrip("/")
    resources: list[ResourceSample] = []
    stop = Event()
    sampler = None
    if args.pid:
        sampler = Thread(target=sample_process, args=(args.pid, stop, resources, 0.1), daemon=True)
        sampler.start()

    print(f"Benchmarking {len(paths)} page(s), {args.repeat} request(s) each against {base_url}")
    print("Page                                       HTTP  timing and payload")
    print("-" * 112)
    slowest: tuple[str, float] | None = None
    all_samples: list[Sample] = []
    try:
        for path in paths:
            page_samples = [measure(f"{base_url}{path}", args.cookie, args.timeout) for _ in range(args.repeat)]
            all_samples.extend(page_samples)
            summarize(path, page_samples)
            average = statistics.mean(sample.total_ms for sample in page_samples)
            if slowest is None or average > slowest[1]:
                slowest = (path, average)
    except RuntimeError as error:
        print(f"\nBenchmark could not connect: {error}")
        print("Start the application first with `make backend` or `docker compose up -d`.")
        return 2
    finally:
        stop.set()
        if sampler:
            sampler.join(timeout=1)

    if slowest:
        print(f"\nSlowest page: {slowest[0]} ({slowest[1]:.1f} ms average)")
    if any(sample.final_url.rstrip("/").endswith("/login") for sample in all_samples):
        print("Warning: at least one page redirected to /login. Pass --cookie to benchmark authenticated pages.")
    if resources:
        print(
            f"Server usage during test: CPU avg {statistics.mean(s.cpu_percent for s in resources):.1f}% "
            f"/ peak {max(s.cpu_percent for s in resources):.1f}%, "
            f"RSS peak {max(s.rss_mb for s in resources):.1f} MB"
        )
    elif args.pid:
        print("Server usage unavailable: the supplied PID exited or could not be sampled.")
    else:
        print("Server CPU not measured. Add --pid <server-pid> to identify processing-heavy pages.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
