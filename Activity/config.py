"""
Configuration settings for the EC2 Student Deployment, Load Testing, and Cleanup.
Reads values from .env automatically.
"""

import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"

# Load .env file
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=ENV_FILE)
except ImportError:
    pass

def clean_env(key, default=""):
    val = os.getenv(key, default)
    if val is None:
        return default
    return str(val).strip().strip("\"'").strip()

# SSH Keys Directory: defaults to ./ssh_files
KEYS_DIR_NAME = clean_env("SSH_KEYS_DIR", "ssh_files")
KEYS_DIR = Path(KEYS_DIR_NAME) if Path(KEYS_DIR_NAME).is_absolute() else BASE_DIR / KEYS_DIR_NAME

# File Paths
STUDENTS_CSV = BASE_DIR / "students.csv"
INVENTORY_CSV = BASE_DIR / "students_inventory.csv"
INVENTORY_JSON = BASE_DIR / "students_inventory.json"
LOAD_TEST_REPORT_CSV = BASE_DIR / "load_test_results.csv"

# AWS Configuration
AWS_REGION = clean_env("AWS_REGION", clean_env("AWS_DEFAULT_REGION", "ap-south-1"))

# VPC & Subnet configuration (optional; if empty, will auto-detect public subnet)
VPC_ID = clean_env("VPC_ID", "")
SUBNET_ID = clean_env("SUBNET_ID", "")

# Tagging for uniform resource management and safe cleanup
PROJECT_TAG_KEY = "Project"
PROJECT_TAG_VALUE = clean_env("PROJECT_TAG_VALUE", "StudentLabActivity")

# Instance configurations
STUDENT_INSTANCE_TYPE = clean_env("STUDENT_INSTANCE_TYPE", "t3.medium")
LOAD_TESTER_INSTANCE_TYPE = clean_env("LOAD_TESTER_INSTANCE_TYPE", "c5.2xlarge")

# Number of student instances to launch (None = all rows in students.csv)
raw_count = clean_env("NUMBER_OF_INSTANCES", "")
try:
    NUMBER_OF_INSTANCES = int(raw_count) if raw_count else None
except ValueError:
    NUMBER_OF_INSTANCES = None

# Security Group configuration
SECURITY_GROUP_NAME = clean_env("SECURITY_GROUP_NAME", "student-lab-shared-sg")
SECURITY_GROUP_DESCRIPTION = "Shared SG for Student Lab - SSH (22) and Backend App"

# Application Target Port
TARGET_APP_PORT = int(clean_env("TARGET_APP_PORT", "3000"))

# Ports to open in the Security Group
INBOUND_RULES = [
    {
        "IpProtocol": "tcp",
        "FromPort": 22,
        "ToPort": 22,
        "IpRanges": [{"CidrIp": "0.0.0.0/0", "Description": "SSH access"}],
    },
    {
        "IpProtocol": "tcp",
        "FromPort": TARGET_APP_PORT,
        "ToPort": TARGET_APP_PORT,
        "IpRanges": [{"CidrIp": "0.0.0.0/0", "Description": "Backend App port"}],
    },
]

# Ubuntu 22.04 LTS (Jammy) SSM Parameter Path
UBUNTU_AMI_SSM_PATH = clean_env(
    "UBUNTU_AMI_SSM_PATH",
    "/aws/service/canonical/ubuntu/server/22.04/stable/current/amd64/hvm/ebs-gp2/ami-id",
)

# Email Configuration
SMTP_SERVER = clean_env("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(clean_env("SMTP_PORT", "587"))
SMTP_USERNAME = clean_env("SMTP_USERNAME", "")
SMTP_PASSWORD = clean_env("SMTP_PASSWORD", "")
SENDER_EMAIL = clean_env("SENDER_EMAIL", "")

# Load Testing defaults
LOAD_TEST_WORKERS_PER_TARGET = int(clean_env("LOAD_TEST_WORKERS_PER_TARGET", "5"))
LOAD_TEST_DURATION = int(clean_env("LOAD_TEST_DURATION", "30"))

def resolve_network(ec2_client):
    """
    Resolves the target VPC ID and Public Subnet ID.
    If explicitly provided in .env (VPC_ID, SUBNET_ID), verifies and uses them.
    Otherwise, automatically finds the best public subnet attached to an Internet Gateway.
    """
    if SUBNET_ID:
        sub = ec2_client.describe_subnets(SubnetIds=[SUBNET_ID])["Subnets"][0]
        vpc_id = sub["VpcId"]
        return vpc_id, SUBNET_ID

    rts = ec2_client.describe_route_tables()["RouteTables"]
    public_rts = set()
    for rt in rts:
        for route in rt.get("Routes", []):
            if route.get("DestinationCidrBlock") == "0.0.0.0/0" and route.get("GatewayId", "").startswith("igw-"):
                public_rts.add(rt["RouteTableId"])

    subnets = ec2_client.describe_subnets()["Subnets"]
    candidates = []
    for s in subnets:
        vpc = s["VpcId"]
        if VPC_ID and vpc != VPC_ID:
            continue
        
        associated_rt = None
        for rt in rts:
            for a in rt.get("Associations", []):
                if a.get("SubnetId") == s["SubnetId"]:
                    associated_rt = rt
                    break
            if associated_rt:
                break
        if not associated_rt:
            for rt in rts:
                if rt["VpcId"] == vpc and any(a.get("Main") for a in rt.get("Associations", [])):
                    associated_rt = rt
                    break

        if associated_rt and associated_rt["RouteTableId"] in public_rts:
            candidates.append(s)

    if not candidates:
        raise RuntimeError("No public subnet with an Internet Gateway route found! Please specify VPC_ID and SUBNET_ID in .env.")

    # Prioritize subnets with MapPublicIpOnLaunch=True and highest available IP count
    candidates.sort(key=lambda x: (x.get("MapPublicIpOnLaunch", False), x["AvailableIpAddressCount"]), reverse=True)
    best = candidates[0]
    return best["VpcId"], best["SubnetId"]
