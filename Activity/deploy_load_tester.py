"""
deploy_load_tester.py
Provisions 1 high-performance c5.2xlarge EC2 instance for aggressive load testing
of all student backend instances.
"""

import os
import json
import boto3
from botocore.exceptions import ClientError
from pathlib import Path

import config

USERDATA_SCRIPT = """#!/bin/bash
set -e
apt-get update -y
apt-get install -y python3 python3-pip git curl htop apache2-utils
pip3 install aiohttp
echo "Load tester instance initialization complete" > /tmp/load_tester_ready.txt
"""

def main():
    print("=" * 70)
    print("🔥 Provisioning Dedicated High-Performance Load Testing Instance")
    print(f"Region: {config.AWS_REGION} | Type: {config.LOAD_TESTER_INSTANCE_TYPE}")
    print("=" * 70)

    from botocore.config import Config
    retry_config = Config(retries={"max_attempts": 5, "mode": "adaptive"})
    ec2_client = boto3.client("ec2", region_name=config.AWS_REGION, config=retry_config)
    ssm_client = boto3.client("ssm", region_name=config.AWS_REGION, config=retry_config)

    # 1. Resolve Network & Subnet
    vpc_id, subnet_id = config.resolve_network(ec2_client)
    print(f"[+] Using VPC: {vpc_id} | Subnet: {subnet_id}")

    # 2. Fetch AMI
    response = ssm_client.get_parameter(Name=config.UBUNTU_AMI_SSM_PATH)
    ami_id = response["Parameter"]["Value"]
    print(f"[+] Using AMI: {ami_id}")

    # 3. Get Shared Security Group ID
    sgs = ec2_client.describe_security_groups(
        Filters=[
            {"Name": "group-name", "Values": [config.SECURITY_GROUP_NAME]},
            {"Name": "vpc-id", "Values": [vpc_id]},
        ]
    )
    if not sgs["SecurityGroups"]:
        print(f"[-] Security group '{config.SECURITY_GROUP_NAME}' not found in VPC {vpc_id}.")
        print("Please run deploy_students.py first or create the security group.")
        return
    sg_id = sgs["SecurityGroups"][0]["GroupId"]
    print(f"[+] Attached to Shared Security Group: {sg_id}")

    # 4. Create Key Pair for the Load Tester
    key_name = "key-loadtester"
    key_path = config.KEYS_DIR / "loadtester.pem"
    config.KEYS_DIR.mkdir(parents=True, exist_ok=True)

    if key_path.exists():
        try:
            if os.name == "nt":
                import subprocess
                subprocess.run(["icacls", str(key_path), "/grant", f"{os.environ.get('USERNAME', 'Everyone')}:F"], capture_output=True)
            key_path.unlink()
        except Exception:
            pass

    try:
        ec2_client.delete_key_pair(KeyName=key_name)
    except Exception:
        pass

    key_res = ec2_client.create_key_pair(
        KeyName=key_name,
        KeyType="rsa",
        KeyFormat="pem",
        TagSpecifications=[
            {
                "ResourceType": "key-pair",
                "Tags": [
                    {"Key": config.PROJECT_TAG_KEY, "Value": config.PROJECT_TAG_VALUE},
                    {"Key": "Role", "Value": "LoadTester"},
                ],
            }
        ],
    )
    with open(key_path, "w", newline="", encoding="utf-8") as f:
        f.write(key_res["KeyMaterial"])

    if os.name != "nt":
        os.chmod(key_path, 0o400)
    print(f"[+] Created Key Pair: {key_name} -> {key_path}")

    # 5. Launch the c5.2xlarge Instance
    print(f"[+] Launching {config.LOAD_TESTER_INSTANCE_TYPE} instance...")
    res = ec2_client.run_instances(
        ImageId=ami_id,
        InstanceType=config.LOAD_TESTER_INSTANCE_TYPE,
        KeyName=key_name,
        MinCount=1,
        MaxCount=1,
        UserData=USERDATA_SCRIPT,
        NetworkInterfaces=[
            {
                "DeviceIndex": 0,
                "SubnetId": subnet_id,
                "AssociatePublicIpAddress": True,
                "Groups": [sg_id],
                "DeleteOnTermination": True,
            }
        ],
        TagSpecifications=[
            {
                "ResourceType": "instance",
                "Tags": [
                    {"Key": "Name", "Value": "load-tester-c5-2xlarge"},
                    {"Key": config.PROJECT_TAG_KEY, "Value": config.PROJECT_TAG_VALUE},
                    {"Key": "Role", "Value": "LoadTester"},
                ],
            }
        ],
    )

    instance_id = res["Instances"][0]["InstanceId"]
    print(f"[+] Instance ID: {instance_id}")

    # 6. Wait until running
    print("[+] Waiting for load tester instance to reach 'running' status...")
    waiter = ec2_client.get_waiter("instance_running")
    waiter.wait(InstanceIds=[instance_id])

    desc = ec2_client.describe_instances(InstanceIds=[instance_id])
    inst = desc["Reservations"][0]["Instances"][0]
    public_ip = inst.get("PublicIpAddress", "N/A")
    public_dns = inst.get("PublicDnsName", "N/A")

    load_tester_info = {
        "instance_id": instance_id,
        "instance_type": config.LOAD_TESTER_INSTANCE_TYPE,
        "public_ip": public_ip,
        "public_dns": public_dns,
        "key_file": str(key_path),
        "ssh_command": f"ssh -i \"{key_path}\" ubuntu@{public_ip}",
    }

    out_file = config.BASE_DIR / "load_tester_info.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(load_tester_info, f, indent=2)

    print("\n" + "=" * 70)
    print("✅ LOAD TESTER PROVISIONED SUCCESSFULLY!")
    print(f"Instance ID:   {instance_id}")
    print(f"Public IP:     {public_ip}")
    print(f"Public DNS:    {public_dns}")
    print(f"SSH Command:   ssh -i \"{key_path}\" ubuntu@{public_ip}")
    print(f"Info saved to: {out_file}")
    print("=" * 70)

if __name__ == "__main__":
    main()
