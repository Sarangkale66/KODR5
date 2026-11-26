"""
undeploy_all.py
Completely terminates all AWS resources created for this activity:
- Terminates all 50 student t3.medium EC2 instances + load tester instance
- Deletes all unique AWS Key Pairs from EC2
- Deletes the shared Security Group
- Deletes local .pem files in the keys/ directory
"""

import sys
import shutil
import argparse
import boto3
from botocore.exceptions import ClientError
from pathlib import Path

import config

def terminate_all_instances(ec2_client):
    """Finds and terminates all instances tagged with Project=StudentLabActivity."""
    print("[+] Searching for instances with tag Project=StudentLabActivity...")
    filters = [
        {"Name": f"tag:{config.PROJECT_TAG_KEY}", "Values": [config.PROJECT_TAG_VALUE]},
        {"Name": "instance-state-name", "Values": ["pending", "running", "stopping", "stopped"]},
    ]
    
    response = ec2_client.describe_instances(Filters=filters)
    instance_ids = []
    for res in response["Reservations"]:
        for inst in res["Instances"]:
            instance_ids.append(inst["InstanceId"])

    if not instance_ids:
        print("[+] No active instances found to terminate.")
        return []

    print(f"[+] Found {len(instance_ids)} instances. Initiating termination...")
    ec2_client.terminate_instances(InstanceIds=instance_ids)
    
    print("[+] Waiting for all instances to reach 'terminated' state (this may take 1-2 minutes)...")
    waiter = ec2_client.get_waiter("instance_terminated")
    waiter.wait(InstanceIds=instance_ids)
    print("  ✓ All instances have been TERMINATED.")
    return instance_ids

def delete_all_key_pairs(ec2_client):
    """Deletes all EC2 Key Pairs created for this project in AWS."""
    print("\n[+] Deleting AWS EC2 Key Pairs...")
    # Fetch key pairs tagged with Project=StudentLabActivity or starting with key-student / key-loadtester
    try:
        keys_res = ec2_client.describe_key_pairs(
            Filters=[{"Name": f"tag:{config.PROJECT_TAG_KEY}", "Values": [config.PROJECT_TAG_VALUE]}]
        )
        key_names = [k["KeyName"] for k in keys_res.get("KeyPairs", [])]
    except Exception:
        key_names = []

    # Also check local keys directory to catch any untagged keys by name
    if config.KEYS_DIR.exists():
        for p in config.KEYS_DIR.glob("*.pem"):
            kname = f"key-{p.stem}"
            if kname not in key_names:
                key_names.append(kname)

    deleted_count = 0
    for name in set(key_names):
        try:
            ec2_client.delete_key_pair(KeyName=name)
            deleted_count += 1
        except Exception as e:
            print(f"  ✗ Failed to delete key {name}: {e}")

    print(f"  ✓ Deleted {deleted_count} EC2 Key Pairs from AWS.")

def delete_security_group(ec2_client):
    """Deletes the shared security group once all instances have terminated."""
    print(f"\n[+] Deleting Security Group: '{config.SECURITY_GROUP_NAME}'...")
    try:
        sgs = ec2_client.describe_security_groups(
            Filters=[{"Name": "group-name", "Values": [config.SECURITY_GROUP_NAME]}]
        )
        if not sgs["SecurityGroups"]:
            print(f"  ✓ Security group '{config.SECURITY_GROUP_NAME}' does not exist.")
            return

        sg_id = sgs["SecurityGroups"][0]["GroupId"]
        
        # Retry loop to account for AWS EC2 instance network interface detachment delay
        max_retries = 10
        for attempt in range(1, max_retries + 1):
            try:
                ec2_client.delete_security_group(GroupId=sg_id)
                print(f"  ✓ Successfully deleted Security Group {sg_id}.")
                return
            except ClientError as e:
                if "DependencyViolation" in str(e) and attempt < max_retries:
                    print(f"  [-] Waiting for ENI detachment (attempt {attempt}/{max_retries})...")
                    import time
                    time.sleep(5)
                else:
                    raise
    except Exception as e:
        print(f"  ✗ Error deleting Security Group: {e}")

def clean_local_files():
    """Deletes local .pem files in ssh_files directory."""
    print(f"\n[+] Cleaning up local key files in {config.KEYS_DIR}...")
    if config.KEYS_DIR.exists():
        import subprocess
        for p in config.KEYS_DIR.glob("*.pem"):
            try:
                if os.name == "nt":
                    subprocess.run(["icacls", str(p), "/grant", f"{os.environ.get('USERNAME', 'Everyone')}:F"], capture_output=True)
                p.unlink()
            except Exception:
                pass
        try:
            shutil.rmtree(config.KEYS_DIR)
        except Exception:
            pass
        print(f"  ✓ Cleaned up local .pem files and {config.KEYS_DIR} directory.")
    else:
        print(f"  ✓ Local directory {config.KEYS_DIR} is already clean.")

def main():
    parser = argparse.ArgumentParser(description="Teardown all AWS resources created for the student lab.")
    parser.add_argument("--force", action="store_true", help="Skip confirmation prompt and terminate immediately.")
    args = parser.parse_args()

    print("=" * 70)
    print("🚨 TEARDOWN & UNDEPLOYMENT SCRIPT")
    print(f"Region: {config.AWS_REGION}")
    print("=" * 70)

    if not args.force:
        confirm = input("⚠️ Are you sure you want to TERMINATE all student & load tester instances, delete AWS keys, and remove local .pem files? (yes/no): ").strip().lower()
        if confirm != "yes":
            print("[+] Teardown cancelled by user.")
            sys.exit(0)

    from botocore.config import Config
    retry_config = Config(retries={"max_attempts": 5, "mode": "adaptive"})
    ec2_client = boto3.client("ec2", region_name=config.AWS_REGION, config=retry_config)

    # 1. Terminate EC2 Instances
    terminate_all_instances(ec2_client)

    # 2. Delete AWS Key Pairs
    delete_all_key_pairs(ec2_client)

    # 3. Delete Shared Security Group
    delete_security_group(ec2_client)

    # 4. Clean local .pem files
    clean_local_files()

    print("\n" + "=" * 70)
    print("✅ TEARDOWN COMPLETED SUCCESSFULLY!")
    print("All AWS instances, security groups, key pairs, and local keys have been wiped.")
    print("=" * 70)

if __name__ == "__main__":
    main()
