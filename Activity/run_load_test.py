"""
run_load_test.py
Aggressive & Educational Multi-Target Load Testing Engine.
Designed to push student EC2 instances to their limits (100% CPU, high latency, 502/504 errors)
to vividly demonstrate why Auto Scaling Groups (ASG) and Load Balancers (ALB) are essential.
"""

import sys
import csv
import time
import asyncio
import argparse
from pathlib import Path
import config

try:
    import aiohttp
except ImportError:
    print("[-] 'aiohttp' library is required. Install it using: pip install aiohttp")
    sys.exit(1)

class FleetMonitor:
    """Tracks global statistics and real-time health across the entire fleet."""
    def __init__(self, targets):
        self.targets = targets
        self.start_time = None
        self.total_requests = 0
        self.success_2xx = 0
        self.client_errors_4xx = 0
        self.server_errors_5xx = 0
        self.timeouts = 0
        self.connection_refused = 0
        self.latencies = []
        self.per_student = {
            t["student_id"]: {
                "url": t["application_url"],
                "total": 0,
                "success": 0,
                "5xx": 0,
                "timeouts": 0,
                "refused": 0,
                "latencies": [],
                "state": "🟢 HEALTHY",
            }
            for t in targets
        }

    def record(self, student_id, status_code, latency_ms, err_type=None):
        self.total_requests += 1
        sdata = self.per_student[student_id]
        sdata["total"] += 1

        if err_type == "timeout":
            self.timeouts += 1
            sdata["timeouts"] += 1
            sdata["state"] = "🔴 FAILING (TIMEOUT)"
        elif err_type == "connection_refused":
            self.connection_refused += 1
            sdata["refused"] += 1
            sdata["state"] = "💀 CRASHED (REFUSED)"
        elif status_code:
            self.latencies.append(latency_ms)
            sdata["latencies"].append(latency_ms)

            if 200 <= status_code < 300:
                self.success_2xx += 1
                sdata["success"] += 1
                if latency_ms > 1500:
                    sdata["state"] = "🟡 DEGRADED (HIGH LATENCY)"
                elif sdata["state"] not in ["🔴 FAILING (TIMEOUT)", "💀 CRASHED (REFUSED)"]:
                    sdata["state"] = "🟢 HEALTHY"
            elif 400 <= status_code < 500:
                self.client_errors_4xx += 1
            elif 500 <= status_code < 600:
                self.server_errors_5xx += 1
                sdata["5xx"] += 1
                sdata["state"] = "🔴 FAILING (5xx ERRORS)"

async def live_dashboard(monitor, duration_sec):
    """Prints a dynamic live status dashboard every second during the attack."""
    start_time = time.time()
    last_count = 0

    while time.time() - start_time < duration_sec:
        await asyncio.sleep(1.0)
        elapsed = time.time() - start_time
        current_total = monitor.total_requests
        current_rps = (current_total - last_count)
        last_count = current_total

        # Compute current avg latency
        recent_lats = monitor.latencies[-100:] if monitor.latencies else [0]
        avg_lat = sum(recent_lats) / len(recent_lats) if recent_lats else 0

        # Count crashed/failing instances
        crashed_count = sum(1 for s in monitor.per_student.values() if "CRASHED" in s["state"])
        failing_count = sum(1 for s in monitor.per_student.values() if "FAILING" in s["state"])
        healthy_count = len(monitor.per_student) - crashed_count - failing_count

        sys.stdout.write(
            f"\r⏱️  [{elapsed:04.1f}s/{duration_sec}s] "
            f"⚡ RPS: {current_rps:5,d} req/s | "
            f"Total: {current_total:7,d} | "
            f"Avg Lat: {avg_lat:6.1f}ms | "
            f"🟢 Up: {healthy_count} | "
            f"🔴 Overloaded: {failing_count} | "
            f"💀 Crashed: {crashed_count}   "
        )
        sys.stdout.flush()

    print()

async def aggressive_blaster(session, target_url, student_id, monitor, deadline, timeout_sec, mode):
    """Fires non-stop pipelined HTTP requests designed to saturate and choke the backend."""
    timeout = aiohttp.ClientTimeout(total=timeout_sec, connect=min(timeout_sec, 0.5))
    
    # In lethal mode, use Connection: close to exhaust OS sockets and trigger connection drops
    conn_header = "close" if mode == "lethal" else "keep-alive"
    headers = {
        "User-Agent": "AggressiveLoadTester/3.0",
        "Accept": "*/*",
        "Connection": conn_header,
    }

    while time.time() < deadline:
        start = time.perf_counter()
        try:
            async with session.get(target_url, headers=headers, timeout=timeout) as resp:
                await resp.read()
                latency_ms = (time.perf_counter() - start) * 1000.0
                monitor.record(student_id, resp.status, latency_ms)
        except asyncio.TimeoutError:
            monitor.record(student_id, None, 0, err_type="timeout")
        except (aiohttp.ClientConnectorError, aiohttp.ServerDisconnectedError):
            monitor.record(student_id, None, 0, err_type="connection_refused")
        except Exception:
            monitor.record(student_id, None, 0, err_type="connection_refused")

async def run_fleet_attack(targets, workers_per_target, duration_sec, timeout_sec, path, mode):
    total_concurrency = len(targets) * workers_per_target
    print("\n" + "=" * 80)
    print(f"🔥 BRUTAL LOAD TEST INITIATED [MODE: {mode.upper()}]")
    print(f"Target Fleet:       {len(targets)} student instances")
    print(f"Workers / Target:   {workers_per_target} parallel connections per instance")
    print(f"Total Concurrency:  {total_concurrency:,} simultaneous connections blasting the fleet")
    print(f"Duration:           {duration_sec} seconds")
    print(f"Target Path:        {path}")
    print("=" * 80)

    monitor = FleetMonitor(targets)
    monitor.start_time = time.time()

    # Ultra-high performance TCP connector configuration
    connector = aiohttp.TCPConnector(
        limit=0,                 # No total connection limit
        limit_per_host=0,        # No per-host limit
        ttl_dns_cache=600,       # Keep DNS cached to maximize HTTP throughput
        use_dns_cache=True,
        keepalive_timeout=30,
        enable_cleanup_closed=True,
    )

    deadline = time.time() + duration_sec

    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = []
        for item in targets:
            sid = item["student_id"]
            base_url = item["application_url"].rstrip("/")
            full_url = f"{base_url}{path}"

            for _ in range(workers_per_target):
                tasks.append(
                    aggressive_blaster(session, full_url, sid, monitor, deadline, timeout_sec, mode)
                )

        # Launch the live visual dashboard concurrently
        dashboard_task = asyncio.create_task(live_dashboard(monitor, duration_sec))

        # Launch all workers
        await asyncio.gather(*tasks, return_exceptions=True)
        await dashboard_task

    total_time = time.time() - monitor.start_time
    return monitor, total_time

def main():
    parser = argparse.ArgumentParser(
        description="Brutal load testing engine designed to stress & demonstrate single-instance failure."
    )
    parser.add_argument(
        "--mode",
        choices=["normal", "heavy", "crush", "lethal"],
        default="lethal",
        help="Attack intensity mode: normal (15), heavy (60), crush (150), lethal (400 workers + socket flood).",
    )
    parser.add_argument(
        "--workers-per-target",
        type=int,
        default=None,
        help="Override concurrent connections per student target.",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=config.LOAD_TEST_DURATION,
        help=f"Test duration in seconds (default: {config.LOAD_TEST_DURATION}).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=None,
        help="Request timeout in seconds (default: 0.8s for lethal, 1.5s for normal).",
    )
    parser.add_argument(
        "--path",
        type=str,
        default="/",
        help="URL path to hit (e.g. '/' or '/api/data').",
    )
    args = parser.parse_args()

    # Determine workers and timeout based on mode
    if args.workers_per_target is not None:
        workers = args.workers_per_target
    else:
        mode_map = {"normal": 15, "heavy": 60, "crush": 150, "lethal": 400}
        workers = mode_map.get(args.mode, 400)

    if args.timeout is not None:
        timeout_val = args.timeout
    else:
        timeout_val = 0.8 if args.mode == "lethal" else 1.5

    if not config.INVENTORY_CSV.exists():
        print(f"[-] Error: {config.INVENTORY_CSV} not found! Deploy fleet first.")
        sys.exit(1)

    targets = []
    with open(config.INVENTORY_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            targets.append(row)

    if not targets:
        print("[-] No targets found in inventory CSV.")
        sys.exit(1)

    # Execute the load test
    monitor, elapsed = asyncio.run(
        run_fleet_attack(
            targets=targets,
            workers_per_target=workers,
            duration_sec=args.duration,
            timeout_sec=timeout_val,
            path=args.path,
            mode=args.mode,
        )
    )

    # Compile CSV Report
    report_rows = []
    for sid, sdata in monitor.per_student.items():
        sorted_lats = sorted(sdata["latencies"])
        p50 = sorted_lats[int(len(sorted_lats) * 0.50)] if sorted_lats else 0
        p90 = sorted_lats[int(len(sorted_lats) * 0.90)] if sorted_lats else 0
        p99 = sorted_lats[int(len(sorted_lats) * 0.99)] if sorted_lats else 0
        avg_lat = sum(sorted_lats) / len(sorted_lats) if sorted_lats else 0

        report_rows.append({
            "student_id": sid,
            "target_url": sdata["url"],
            "status": sdata["state"],
            "total_requests": sdata["total"],
            "success_2xx": sdata["success"],
            "5xx_errors": sdata["5xx"],
            "timeouts": sdata["timeouts"],
            "refused_dropped": sdata["refused"],
            "avg_latency_ms": round(avg_lat, 2),
            "p50_ms": round(p50, 2),
            "p90_ms": round(p90, 2),
            "p99_ms": round(p99, 2),
        })

    fieldnames = [
        "student_id",
        "target_url",
        "status",
        "total_requests",
        "success_2xx",
        "5xx_errors",
        "timeouts",
        "refused_dropped",
        "avg_latency_ms",
        "p50_ms",
        "p90_ms",
        "p99_ms",
    ]
    with open(config.LOAD_TEST_REPORT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(report_rows)

    overall_rps = monitor.total_requests / elapsed if elapsed > 0 else 0

    # Print Summary & Student Breakdown Table
    print("\n" + "=" * 80)
    print("📊 POST-ATTACK FLEET REPORT & RANKINGS")
    print("=" * 80)
    print(f"{'Student ID':<15} | {'Status':<25} | {'Requests':<10} | {'Success':<8} | {'Errors/Drop':<12} | {'P90 Latency'}")
    print("-" * 80)
    for r in report_rows[:15]:  # Show top 15 preview in terminal
        print(
            f"{r['student_id']:<15} | "
            f"{r['status']:<25} | "
            f"{r['total_requests']:<10,d} | "
            f"{r['success_2xx']:<8,d} | "
            f"{r['timeouts'] + r['refused_dropped'] + r['5xx_errors']:<12,d} | "
            f"{r['p90_ms']} ms"
        )
    if len(report_rows) > 15:
        print(f"... and {len(report_rows) - 15} more students recorded in {config.LOAD_TEST_REPORT_CSV.name}")

    print("=" * 80)
    print(f"Total Traffic Dispatched: {monitor.total_requests:,} requests")
    print(f"Peak Throughput:          {overall_rps:,.2f} req/second")
    print(f"Total 2xx Successes:      {monitor.success_2xx:,}")
    print(f"Total Overloaded/Dropped: {monitor.timeouts + monitor.connection_refused + monitor.server_errors_5xx:,}")
    print("=" * 80)

    # 🎓 EDUCATIONAL LESSON FOR STUDENTS:
    print("\n" + "🎓 " + "=" * 76)
    print("💡 EDUCATIONAL LESSON: WHY DID THE SERVERS CRASH?")
    print("=" * 80)
    print("1. Single Point of Failure (SPOF):")
    print("   Each student had a single t3.medium instance. When thousands of concurrent")
    print("   requests arrived, the single CPU reached 100% and burst credits depleted.")
    print("\n2. Event Loop & Socket Starvation:")
    print("   The OS connection queue filled up, causing high latency, connection resets,")
    print("   and 502/504 gateway timeout errors.")
    print("\n3. THE SOLUTION (NEXT TOPIC):")
    print("   👉 AWS Auto Scaling Groups (ASG) + Application Load Balancer (ALB)")
    print("   - Automatically spins up new EC2 instances when CPU > 70%")
    print("   - Distributes incoming traffic evenly across healthy instances")
    print("   - Self-heals: automatically replaces unhealthy instances")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    main()
