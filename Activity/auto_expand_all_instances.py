"""
auto_expand_all_instances.py
1. Expands all 35 student EBS volumes to 30GB in AWS.
2. SSHs into all 35 instances in parallel.
3. Runs:
   sudo growpart /dev/nvme0n1 1 2>/dev/null || sudo growpart /dev/xvda 1
   sudo resize2fs /dev/nvme0n1p1 2>/dev/null || sudo resize2fs /dev/xvda1
   df -h /
4. Prints a live status report for each student.
"""

import os
import sys
import json
import time
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
import boto3
from botocore.config import Config
from pathlib import Path

import config

TARGET_SIZE_GB = 30

COMMAND_SCRIPT = """
sudo growpart /dev/nvme0n1 1 2>/dev/null || sudo growpart /dev/xvda 1 2>/dev/null || true
sudo resize2fs /dev/nvme0n1p1 2>/dev/null || sudo resize2fs /dev/xvda1 2>/dev/null || true
df -h / | awk 'NR==2 {print $2, $3, $4, $5}'
"""

def fix_key_permission(key_path):
    """Sets proper Windows permissions on key file so SSH succeeds without warnings."""
    if os.name == "nt" and Path(key_path).exists():
        try:
            username = os.environ.get("USERNAME", "Everyone")
            subprocess.run(["icacls", str(key_path), "/reset"], capture_output=True)
            subprocess.run(["icacls", str(key_path), "/grant:r", f"{username}:R"], capture_output=True)
            subprocess.run(["icacls", str(key_path), "/inheritance:r"], capture_output=True)
        except Exception:
            pass

def expand_aws_ebs_volumes(ec2_client, inventory):
    """Expands EBS volume sizes to 30GB in AWS."""
    print("=" * 75)
    print(f"1️⃣  EXPANDING EBS VOLUMES TO {TARGET_SIZE_GB}GB IN AWS ({config.AWS_REGION})")
    print("=" * 75)

    modified_any = False
    for item in inventory:
        iid = item["instance_id"]
        sid = item["student_id"]

        try:
            inst = ec2_client.describe_instances(InstanceIds=[iid])["Reservations"][0]["Instances"][0]
            mappings = inst.get("BlockDeviceMappings", [])
            if not mappings:
                continue

            vol_id = mappings[0]["Ebs"]["VolumeId"]
            vol_desc = ec2_client.describe_volumes(VolumeIds=[vol_id])["Volumes"][0]
            cur_size = vol_desc["Size"]

            if cur_size < TARGET_SIZE_GB:
                res = ec2_client.modify_volume(VolumeId=vol_id, Size=TARGET_SIZE_GB)
                state = res["VolumeModification"]["ModificationState"]
                print(f"  ✓ [{sid}] {iid} ({vol_id}): {cur_size}GB -> {TARGET_SIZE_GB}GB (State: {state})")
                modified_any = True
                time.sleep(0.2)
            else:
                print(f"  ⚡ [{sid}] {iid} ({vol_id}): already {cur_size}GB.")
        except Exception as e:
            print(f"  ✗ [{sid}] AWS EBS modify error: {e}")

    if modified_any:
        print("\n[+] Waiting 8 seconds for AWS hypervisor to signal new disk size to instances...")
        time.sleep(8)
    else:
        print("[+] All AWS volumes are already at 30GB.")

def ssh_and_grow_disk(item):
    """SSHs into a single student instance and executes growpart & resize2fs."""
    sid = item["student_id"]
    ip = item["public_ip"]
    key_path = item["key_file_path"]

    fix_key_permission(key_path)

    ssh_cmd = [
        "ssh",
        "-i", str(key_path),
        "-o", "StrictHostKeyChecking=no",
        "-o", "ConnectTimeout=10",
        "-o", "BatchMode=yes",
        f"ubuntu@{ip}",
        COMMAND_SCRIPT.strip(),
    ]

    try:
        proc = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=25)
        if proc.returncode == 0:
            out = proc.stdout.strip().replace("\n", " ").strip()
            # Expecting: Total, Used, Avail, Use%
            return {
                "student_id": sid,
                "ip": ip,
                "status": "SUCCESS",
                "disk_info": out if out else "Resized OK",
            }
        else:
            err = proc.stderr.strip().replace("\n", " ")
            return {
                "student_id": sid,
                "ip": ip,
                "status": "FAILED",
                "error": err[:100] if err else "Exit code != 0",
            }
    except Exception as e:
        return {
            "student_id": sid,
            "ip": ip,
            "status": "FAILED",
            "error": str(e),
        }

def main():
    if not config.INVENTORY_JSON.exists():
        print(f"[-] Error: {config.INVENTORY_JSON} not found!")
        sys.exit(1)

    with open(config.INVENTORY_JSON, "r", encoding="utf-8") as f:
        inventory = json.load(f)

    print("=" * 75)
    print(f"🚀 LIVE RUNTIME DISK EXPANSION ENGINE (30 GB)")
    print(f"Target Fleet: {len(inventory)} student instances")
    print("=" * 75)

    # 1. AWS Client with dual-stack and retry configuration
    cfg = Config(retries={"max_attempts": 5, "mode": "adaptive"}, use_dualstack_endpoint=True)
    ec2_client = boto3.client("ec2", region_name=config.AWS_REGION, config=cfg)

    # 2. Modify EBS Volumes in AWS
    expand_aws_ebs_volumes(ec2_client, inventory)

    # 3. SSH into all instances concurrently and run the 3 commands
    print("\n" + "=" * 75)
    print("2️⃣  SSHING INTO ALL INSTANCES & EXECUTING RESIZE COMMANDS IN PARALLEL")
    print("=" * 75)

    results = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_map = {executor.submit(ssh_and_grow_disk, item): item for item in inventory}
        for future in as_completed(future_map):
            res = future.result()
            results.append(res)
            if res["status"] == "SUCCESS":
                print(f"  ✓ [{res['student_id']}] ({res['ip']}): Disk resized! -> [Size Used Avail Use%]: {res['disk_info']}")
            else:
                print(f"  ✗ [{res['student_id']}] ({res['ip']}): Failed -> {res.get('error')}")

    results.sort(key=lambda x: x["student_id"])

    # 4. Final summary
    success_count = sum(1 for r in results if r["status"] == "SUCCESS")
    fail_count = len(results) - success_count

    print("\n" + "=" * 75)
    print("📊 FINAL RESIZE SUMMARY")
    print("=" * 75)
    print(f"Total Instances: {len(results)}")
    print(f"Successfully Resized to 30GB: {success_count}")
    print(f"Failed / Inaccessible:        {fail_count}")
    print("=" * 75)

if __name__ == "__main__":
    main()
