"""
expand_all_volumes.py
Modifies the EBS volume size of all student EC2 instances to 30GB in AWS.
Zero-downtime, runtime modification.
"""

import time
import boto3
from botocore.config import Config
import config

TARGET_SIZE_GB = 30

def main():
    print("=" * 70)
    print(f"🚀 Expanding all student EBS volumes to {TARGET_SIZE_GB} GB in AWS ({config.AWS_REGION})")
    print("=" * 70)

    cfg = Config(retries={"max_attempts": 5, "mode": "adaptive"}, use_dualstack_endpoint=True)
    ec2_client = boto3.client("ec2", region_name=config.AWS_REGION, config=cfg)

    # 1. Fetch all student instances
    filters = [
        {"Name": f"tag:{config.PROJECT_TAG_KEY}", "Values": [config.PROJECT_TAG_VALUE]},
        {"Name": "instance-state-name", "Values": ["running", "pending", "stopped"]},
    ]
    res = ec2_client.describe_instances(Filters=filters)

    instances = []
    for r in res["Reservations"]:
        for inst in r["Instances"]:
            instances.append(inst)

    print(f"[+] Found {len(instances)} student instances in {config.AWS_REGION}.")
    if not instances:
        return

    # 2. Modify volumes
    success_count = 0
    skipped_count = 0

    for inst in instances:
        iid = inst["InstanceId"]
        name_tag = next((t["Value"] for t in inst.get("Tags", []) if t["Key"] == "Name"), iid)

        mappings = inst.get("BlockDeviceMappings", [])
        if not mappings:
            print(f"[-] No EBS mappings found for {name_tag} ({iid})")
            continue

        vol_id = mappings[0]["Ebs"]["VolumeId"]

        # Check current volume size
        vol_info = ec2_client.describe_volumes(VolumeIds=[vol_id])["Volumes"][0]
        cur_size = vol_info["Size"]

        if cur_size >= TARGET_SIZE_GB:
            print(f"  ⚡ {name_tag} ({vol_id}) already {cur_size} GB. Skipped.")
            skipped_count += 1
            continue

        try:
            mod_res = ec2_client.modify_volume(VolumeId=vol_id, Size=TARGET_SIZE_GB)
            state = mod_res["VolumeModification"]["ModificationState"]
            print(f"  ✓ {name_tag} ({vol_id}): {cur_size}GB -> {TARGET_SIZE_GB}GB (State: {state})")
            success_count += 1
            time.sleep(0.3)  # Rate limiting
        except Exception as e:
            print(f"  ✗ Failed for {name_tag} ({vol_id}): {e}")

    print("\n" + "=" * 70)
    print(f"✅ AWS Volume Expansion Initiated! Modified: {success_count} | Skipped: {skipped_count}")
    print("=" * 70)
    print("\nNext, students can run these commands inside their Ubuntu terminal:")
    print("  sudo growpart /dev/nvme0n1 1 2>/dev/null || sudo growpart /dev/xvda 1")
    print("  sudo resize2fs /dev/nvme0n1p1 2>/dev/null || sudo resize2fs /dev/xvda1")
    print("  df -h /\n")

if __name__ == "__main__":
    main()
