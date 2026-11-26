"""
deploy_students.py
Automates the provisioning of EC2 instances with unique SSH keys,
a shared security group (ports 22 & 3000), and outputs an inventory CSV/JSON.
"""

import os
import sys
import csv
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import boto3
from botocore.exceptions import ClientError

import config

def get_ec2_clients(region_name=config.AWS_REGION):
    from botocore.config import Config
    retry_config = Config(
        retries={"max_attempts": 5, "mode": "adaptive"},
        connect_timeout=10,
        read_timeout=30,
    )
    ec2_client = boto3.client("ec2", region_name=region_name, config=retry_config)
    ssm_client = boto3.client("ssm", region_name=region_name, config=retry_config)
    return ec2_client, ssm_client

def get_latest_ubuntu_ami(ssm_client):
    """Retrieve the latest official Ubuntu 22.04 LTS AMI ID via SSM."""
    try:
        response = ssm_client.get_parameter(Name=config.UBUNTU_AMI_SSM_PATH)
        ami_id = response["Parameter"]["Value"]
        print(f"[+] Found Ubuntu 22.04 LTS AMI: {ami_id}")
        return ami_id
    except Exception as e:
        print(f"[-] Error fetching AMI from SSM: {e}. Falling back to default search.")
        raise

def get_or_create_security_group(ec2_client, vpc_id):
    """Ensure the shared security group exists in the specified VPC with ports 22 and 3000 open."""
    sg_name = config.SECURITY_GROUP_NAME
    
    # Check if SG already exists in the target VPC
    try:
        response = ec2_client.describe_security_groups(
            Filters=[
                {"Name": "group-name", "Values": [sg_name]},
                {"Name": "vpc-id", "Values": [vpc_id]},
            ]
        )
        if response["SecurityGroups"]:
            sg_id = response["SecurityGroups"][0]["GroupId"]
            print(f"[+] Security Group '{sg_name}' already exists in VPC {vpc_id} ({sg_id})")
            return sg_id
    except ClientError as e:
        print(f"[-] Checking SG error: {e}")

    # Create the Security Group
    print(f"[+] Creating Security Group '{sg_name}' in VPC {vpc_id}...")
    res = ec2_client.create_security_group(
        GroupName=sg_name,
        Description=config.SECURITY_GROUP_DESCRIPTION,
        VpcId=vpc_id,
        TagSpecifications=[
            {
                "ResourceType": "security-group",
                "Tags": [
                    {"Key": config.PROJECT_TAG_KEY, "Value": config.PROJECT_TAG_VALUE},
                    {"Key": "Name", "Value": sg_name},
                ],
            }
        ],
    )
    sg_id = res["GroupId"]
    print(f"[+] Created Security Group '{sg_name}' ({sg_id})")

    # Authorize Inbound Rules
    try:
        ec2_client.authorize_security_group_ingress(
            GroupId=sg_id,
            IpPermissions=config.INBOUND_RULES,
        )
        print(f"[+] Authorized Inbound Rules: Port 22 (SSH) and Port {config.TARGET_APP_PORT} (Backend)")
    except ClientError as e:
        if "InvalidPermission.Duplicate" in str(e):
            pass
        else:
            raise

    return sg_id

def create_unique_key_pair(ec2_client, student_id):
    """Creates a distinct EC2 Key Pair for the student and writes .pem file."""
    key_name = f"key-{student_id}"
    key_path = config.KEYS_DIR / f"{student_id}.pem"

    # Unlock and remove old file if it exists (handles Windows read-only lock)
    if key_path.exists():
        try:
            if os.name == "nt":
                import subprocess
                subprocess.run(["icacls", str(key_path), "/grant", f"{os.environ.get('USERNAME', 'Everyone')}:F"], capture_output=True)
            key_path.unlink()
        except Exception:
            pass

    # If key already exists in AWS, delete it first to ensure clean state
    try:
        ec2_client.delete_key_pair(KeyName=key_name)
    except Exception:
        pass

    res = ec2_client.create_key_pair(
        KeyName=key_name,
        KeyType="rsa",
        KeyFormat="pem",
        TagSpecifications=[
            {
                "ResourceType": "key-pair",
                "Tags": [
                    {"Key": config.PROJECT_TAG_KEY, "Value": config.PROJECT_TAG_VALUE},
                    {"Key": "StudentId", "Value": student_id},
                ],
            }
        ],
    )

    # Save private key to disk
    key_material = res["KeyMaterial"]
    with open(key_path, "w", newline="", encoding="utf-8") as f:
        f.write(key_material)

    # Restrict permissions on Unix/Linux if applicable
    if os.name != "nt":
        os.chmod(key_path, 0o400)

    return key_name, str(key_path)

def launch_single_instance(ec2_client, student, ami_id, sg_id, subnet_id):
    """Worker task to create key and launch a single EC2 instance for a student."""
    student_id = student["student_id"]
    email = student["email"]
    full_name = student.get("full_name", student_id)
    batch = student.get("batch", "")

    key_name, key_file_path = create_unique_key_pair(ec2_client, student_id)

    tags = [
        {"Key": "Name", "Value": f"student-{student_id}"},
        {"Key": "StudentName", "Value": full_name},
        {"Key": "StudentEmail", "Value": email},
        {"Key": "StudentId", "Value": student_id},
        {"Key": config.PROJECT_TAG_KEY, "Value": config.PROJECT_TAG_VALUE},
        {"Key": "Role", "Value": "Student"},
    ]
    if batch:
        tags.append({"Key": "Batch", "Value": batch})

    response = ec2_client.run_instances(
        ImageId=ami_id,
        InstanceType=config.STUDENT_INSTANCE_TYPE,
        KeyName=key_name,
        MinCount=1,
        MaxCount=1,
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
                "Tags": tags,
            }
        ],
    )

    instance_id = response["Instances"][0]["InstanceId"]
    return {
        "student_id": student_id,
        "full_name": full_name,
        "email": email,
        "batch": batch,
        "instance_id": instance_id,
        "key_name": key_name,
        "key_file_path": key_file_path,
    }

def main():
    print("=" * 70)
    print("🚀 AWS EC2 Fleet Provisioner")
    print(f"Region: {config.AWS_REGION} | Type: {config.STUDENT_INSTANCE_TYPE}")
    print("=" * 70)

    # Verify input CSV
    if not config.STUDENTS_CSV.exists():
        print(f"[-] Error: {config.STUDENTS_CSV} not found!")
        sys.exit(1)

    students = []
    with open(config.STUDENTS_CSV, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=1):
            clean = {k.strip(): v.strip() for k, v in row.items() if k and v}
            
            # Find email (supports 'email' or Google Forms long question title)
            email = clean.get("email") or clean.get("Email")
            if not email:
                for k, v in clean.items():
                    if "email" in k.lower():
                        email = v
                        break

            # Find student ID or auto-assign
            sid = clean.get("student_id") or clean.get("Student ID") or f"student-{idx:02d}"

            # Find Full Name
            full_name = clean.get("full_name") or clean.get("Full Name") or clean.get("name") or clean.get("Name") or sid

            # Find Batch
            batch = clean.get("batch") or clean.get("Batch") or ""

            if email:
                students.append({
                    "student_id": sid,
                    "full_name": full_name,
                    "email": email,
                    "batch": batch,
                })

    if config.NUMBER_OF_INSTANCES and config.NUMBER_OF_INSTANCES > 0:
        students = students[:config.NUMBER_OF_INSTANCES]

    total_students = len(students)
    print(f"[+] Loaded {total_students} student entries from {config.STUDENTS_CSV.name}")

    if total_students == 0:
        print("[-] No students found in CSV!")
        sys.exit(1)

    # Create keys directory
    config.KEYS_DIR.mkdir(parents=True, exist_ok=True)

    # Initialize AWS Clients
    ec2_client, ssm_client = get_ec2_clients()

    # 1. Resolve Network (VPC & Public Subnet) and Security Group
    vpc_id, subnet_id = config.resolve_network(ec2_client)
    print(f"[+] Target VPC: {vpc_id} | Public Subnet: {subnet_id}")

    ami_id = get_latest_ubuntu_ami(ssm_client)
    sg_id = get_or_create_security_group(ec2_client, vpc_id)

    # 2. Launch instances concurrently
    print(f"\n[+] Provisioning {total_students} instances in parallel...")
    results = []
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_student = {
            executor.submit(launch_single_instance, ec2_client, s, ami_id, sg_id, subnet_id): s
            for s in students
        }
        for future in as_completed(future_to_student):
            s = future_to_student[future]
            try:
                data = future.result()
                results.append(data)
                print(f"  ✓ Launched {data['student_id']} -> Instance: {data['instance_id']}")
            except Exception as e:
                print(f"  ✗ Failed for {s['student_id']}: {e}")

    print(f"[+] Launched {len(results)}/{total_students} instances in {time.time() - start_time:.1f}s")

    if not results:
        print("[-] No instances were launched. Check the errors above.")
        sys.exit(1)

    # 3. Wait for all instances to reach running status
    instance_ids = [r["instance_id"] for r in results]
    print(f"\n[+] Waiting for all {len(instance_ids)} instances to reach 'running' state...")
    waiter = ec2_client.get_waiter("instance_running")
    waiter.wait(InstanceIds=instance_ids)
    print("[+] All instances are now RUNNING!")

    # 4. Describe instances to collect Public IP and Public DNS
    print("[+] Fetching Public IPs and Public DNS hostnames...")
    desc = ec2_client.describe_instances(InstanceIds=instance_ids)

    lookup = {}
    for res in desc["Reservations"]:
        for inst in res["Instances"]:
            lookup[inst["InstanceId"]] = {
                "public_ip": inst.get("PublicIpAddress", "N/A"),
                "public_dns": inst.get("PublicDnsName", "N/A"),
            }

    # 5. Build final student inventory
    final_inventory = []
    for item in results:
        iid = item["instance_id"]
        ip = lookup.get(iid, {}).get("public_ip", "N/A")
        dns = lookup.get(iid, {}).get("public_dns", "N/A")
        key_file = item["key_file_path"]

        app_url = f"http://{dns}:{config.TARGET_APP_PORT}/" if dns and dns != "N/A" else f"http://{ip}:{config.TARGET_APP_PORT}/"
        ssh_cmd = f"ssh -i \"{key_file}\" ubuntu@{ip}"

        final_inventory.append({
            "student_id": item["student_id"],
            "full_name": item.get("full_name", ""),
            "email": item["email"],
            "batch": item.get("batch", ""),
            "instance_id": iid,
            "public_ip": ip,
            "public_dns": dns,
            "application_url": app_url,
            "ssh_command": ssh_cmd,
            "key_file_path": key_file,
        })

    # Sort by student_id
    final_inventory.sort(key=lambda x: x["student_id"])

    # 6. Save to CSV
    fieldnames = [
        "student_id",
        "full_name",
        "email",
        "batch",
        "instance_id",
        "public_ip",
        "public_dns",
        "application_url",
        "ssh_command",
        "key_file_path",
    ]
    with open(config.INVENTORY_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(final_inventory)

    # 7. Save to JSON
    with open(config.INVENTORY_JSON, "w", encoding="utf-8") as f:
        json.dump(final_inventory, f, indent=2)

    print("\n" + "=" * 70)
    print("✅ DEPLOYMENT COMPLETE!")
    print(f"Inventory CSV saved:  {config.INVENTORY_CSV}")
    print(f"Inventory JSON saved: {config.INVENTORY_JSON}")
    print(f"Total Instances:      {len(final_inventory)}")
    print(f"Keys Directory:       {config.KEYS_DIR}")
    print("=" * 70)

if __name__ == "__main__":
    main()
