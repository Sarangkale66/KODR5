import json
import subprocess
import time
from pathlib import Path

FAILED_STUDENTS = [
    "student-06", "student-11", "student-12", "student-14", "student-15",
    "student-16", "student-17", "student-18", "student-19", "student-20",
    "student-21", "student-25", "student-28", "student-29", "student-33",
    "student-34", "student-35"
]

COMMAND_SCRIPT = """
sudo growpart /dev/nvme0n1 1 2>/dev/null || sudo growpart /dev/xvda 1 2>/dev/null || true
sudo resize2fs /dev/nvme0n1p1 2>/dev/null || sudo resize2fs /dev/xvda1 2>/dev/null || true
df -h / | awk 'NR==2 {print $2, $3, $4, $5}'
"""

def fix_key_permission(key_path):
    try:
        import os
        username = os.environ.get("USERNAME", "Everyone")
        subprocess.run(["icacls", str(key_path), "/reset"], capture_output=True)
        subprocess.run(["icacls", str(key_path), "/grant:r", f"{username}:R"], capture_output=True)
        subprocess.run(["icacls", str(key_path), "/inheritance:r"], capture_output=True)
    except Exception:
        pass

def run():
    with open("students_inventory.json", "r", encoding="utf-8") as f:
        inventory = json.load(f)

    inv_map = {item["student_id"]: item for item in inventory}

    print(f"Retrying {len(FAILED_STUDENTS)} failed instances sequentially with backoff...\n")

    success = []
    failed = []

    for sid in FAILED_STUDENTS:
        item = inv_map.get(sid)
        if not item:
            print(f"[-] {sid} not found in inventory!")
            continue

        ip = item["public_ip"]
        key = item["key_file_path"]
        fix_key_permission(key)

        print(f"Connecting to {sid} ({ip})...", end=" ", flush=True)

        done = False
        for attempt in range(1, 4):
            ssh_cmd = [
                "ssh",
                "-i", str(key),
                "-o", "StrictHostKeyChecking=no",
                "-o", "ConnectTimeout=15",
                "-o", "BatchMode=yes",
                "-o", "ConnectionAttempts=2",
                f"ubuntu@{ip}",
                COMMAND_SCRIPT.strip()
            ]

            try:
                proc = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=30)
                if proc.returncode == 0:
                    out = proc.stdout.strip().replace("\n", " ").strip()
                    print(f"SUCCESS! -> {out}")
                    success.append(sid)
                    done = True
                    break
                else:
                    err = proc.stderr.strip().replace("\n", " ")
                    if attempt < 3:
                        time.sleep(2)
            except Exception as e:
                if attempt < 3:
                    time.sleep(2)

        if not done:
            print("FAILED after 3 attempts.")
            failed.append(sid)

        time.sleep(1)

    print("\n" + "=" * 50)
    print(f"Summary: Success: {len(success)}/{len(FAILED_STUDENTS)}, Failed: {len(failed)}")
    if failed:
        print(f"Still failed: {failed}")

if __name__ == "__main__":
    run()
