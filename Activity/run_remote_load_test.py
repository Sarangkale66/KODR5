"""
run_remote_load_test.py
Executes the aggressive load test directly from the AWS c5.2xlarge instance
using AWS's high-speed 10 Gbps internal backbone network.
"""

import sys
import json
import argparse
import subprocess
from pathlib import Path

import config

def main():
    parser = argparse.ArgumentParser(
        description="Run the aggressive load test from the dedicated AWS c5.2xlarge instance."
    )
    parser.add_argument(
        "--mode",
        choices=["normal", "heavy", "crush", "lethal"],
        default="lethal",
        help="Attack intensity mode: normal, heavy, crush, lethal (default: lethal).",
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
        "--path",
        type=str,
        default="/",
        help="URL path to hit (default: '/').",
    )
    args = parser.parse_args()

    info_file = config.BASE_DIR / "load_tester_info.json"
    if not info_file.exists():
        print("[-] Error: load_tester_info.json not found!")
        print("[-] Please deploy the load tester instance first by running:")
        print("    python deploy_load_tester.py")
        sys.exit(1)

    with open(info_file, "r", encoding="utf-8") as f:
        tester_info = json.load(f)

    public_ip = tester_info["public_ip"]
    key_file = tester_info["key_file"]

    print("=" * 75)
    print("🚀 DISPATCHING LOAD TEST TO DEDICATED AWS LOAD TESTER (c5.2xlarge)")
    print(f"Load Tester IP: {public_ip}")
    print(f"Network Pipe:   Up to 10 Gbps (AWS Internal Backbone)")
    print(f"Attack Mode:    {args.mode.upper()}")
    print("=" * 75)

    # 1. Sync necessary files to the c5.2xlarge instance
    files_to_sync = [
        config.BASE_DIR / "run_load_test.py",
        config.BASE_DIR / "config.py",
        config.BASE_DIR / "students_inventory.csv",
    ]

    for fpath in files_to_sync:
        if not fpath.exists():
            print(f"[-] Error: Required file {fpath.name} not found!")
            sys.exit(1)

        print(f"[+] Uploading {fpath.name} to c5.2xlarge...")
        scp_cmd = [
            "scp",
            "-i", key_file,
            "-o", "StrictHostKeyChecking=no",
            str(fpath),
            f"ubuntu@{public_ip}:~/{fpath.name}",
        ]
        ret = subprocess.run(scp_cmd)
        if ret.returncode != 0:
            print(f"[-] SCP failed for {fpath.name}. Check SSH connectivity.")
            sys.exit(1)

    # 2. Build the remote execution command
    cmd_parts = [
        "python3", "run_load_test.py",
        "--mode", args.mode,
        "--duration", str(args.duration),
        "--path", f'"{args.path}"',
    ]
    if args.workers_per_target:
        cmd_parts.extend(["--workers-per-target", str(args.workers_per_target)])

    remote_cmd = " ".join(cmd_parts)
    print(f"\n[+] Executing remotely on c5.2xlarge: {remote_cmd}")
    print("-" * 75)

    ssh_cmd = [
        "ssh",
        "-t",
        "-i", key_file,
        "-o", "StrictHostKeyChecking=no",
        f"ubuntu@{public_ip}",
        remote_cmd,
    ]

    # Run interactively so the live dashboard streams directly to the local terminal
    subprocess.run(ssh_cmd)

    # 3. Pull back the latest load_test_results.csv from c5.2xlarge to local
    print("\n[+] Downloading load_test_results.csv from c5.2xlarge...")
    pull_cmd = [
        "scp",
        "-i", key_file,
        "-o", "StrictHostKeyChecking=no",
        f"ubuntu@{public_ip}:~/load_test_results.csv",
        str(config.LOAD_TEST_REPORT_CSV),
    ]
    subprocess.run(pull_cmd, capture_output=True)
    print(f"[+] Benchmark results saved locally to: {config.LOAD_TEST_REPORT_CSV}")

if __name__ == "__main__":
    main()
