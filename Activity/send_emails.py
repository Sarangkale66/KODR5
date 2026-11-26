"""
send_emails.py
Dispatches individualized emails to students containing their EC2 Public IP,
Public DNS, App URL (port 3000), SSH command, and attaches their unique .pem key.
"""

import os
import sys
import csv
import smtplib
import argparse
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path

import config

EMAIL_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html>
<head>
  <style>
    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
    .container {{ max-width: 650px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px; }}
    .header {{ background-color: #232f3e; color: #ffffff; padding: 15px; border-radius: 6px 6px 0 0; text-align: center; }}
    .card {{ background: #f9f9f9; padding: 15px; margin: 15px 0; border-left: 4px solid #ff9900; }}
    .code {{ background: #272822; color: #f8f8f2; padding: 10px; border-radius: 4px; font-family: 'Courier New', monospace; font-size: 14px; overflow-x: auto; }}
    .badge {{ display: inline-block; padding: 4px 8px; background: #0073bb; color: white; border-radius: 4px; font-weight: bold; font-size: 12px; }}
    .note {{ background: #fff3cd; color: #856404; padding: 10px; border-radius: 4px; margin-top: 15px; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h2>AWS Backend Activity: EC2 Access Details</h2>
    </div>

    <p>Hello <strong>{full_name}</strong> ({student_id}),</p>
    <p>Your dedicated AWS EC2 instance has been provisioned. Please find your connection credentials and unique SSH private key below.</p>

    <div class="card">
      <p><strong>Instance ID:</strong> {instance_id}</p>
      <p><strong>Public IP Address:</strong> <code>{public_ip}</code></p>
      <p><strong>Public DNS:</strong> <code>{public_dns}</code></p>
      <p><strong>Application URL:</strong> <a href="{application_url}" target="_blank">{application_url}</a></p>
      <p><strong>Attached SSH Key:</strong> <code>{key_filename}</code></p>
    </div>

    <h3>1. Connect via SSH</h3>
    <p>Save the attached <code>{key_filename}</code> file to your computer, open your terminal in that folder, and run:</p>

    <p><strong>Linux / macOS:</strong></p>
    <div class="code">
chmod 400 {key_filename}<br>
ssh -i {key_filename} ubuntu@{public_ip}
    </div>

    <p><strong>Windows (PowerShell):</strong></p>
    <div class="code">
# 1. Reset permissions<br>
icacls "{key_filename}" /reset<br><br>
# 2. Grant read-only access to the current logging-in user<br>
icacls "{key_filename}" /grant:r "$($env:USERNAME):R"<br><br>
# 3. Remove inheritance (removes access for other users/groups)<br>
icacls "{key_filename}" /inheritance:r<br><br>
# 4. Connect via SSH<br>
ssh -i "{key_filename}" ubuntu@{public_ip}
    </div>

    <h3>2. Application Deployment Guidelines</h3>
    <ul>
      <li>Deploy your backend server inside your instance.</li>
      <li><strong>Crucial:</strong> Bind your server to <code>0.0.0.0</code> and port <strong>3000</strong> (e.g. <code>app.listen(3000, "0.0.0.0")</code> in Node.js).</li>
      <li>Verify your app by visiting: <br><a href="{application_url}" target="_blank">{application_url}</a></li>
    </ul>

    <div class="note">
      <strong>⚠️ Warning:</strong> Keep your attached private key safe. Do not share it with other students.
    </div>

    <p>Best regards,<br>Activity Coordination Team</p>
  </div>
</body>
</html>
"""

EMAIL_TEXT_TEMPLATE = """\
AWS Backend Activity: EC2 Access Details
========================================

Hello {full_name} ({student_id}),

Your dedicated AWS EC2 instance is ready.

Instance Details:
- Instance ID:     {instance_id}
- Public IP:       {public_ip}
- Public DNS:      {public_dns}
- Application URL: {application_url}
- Attached Key:    {key_filename}

How to Connect:
1. Save the attached '{key_filename}' to your machine.
2. In your terminal, run:

   Windows (PowerShell):
   # Reset permissions
   icacls "{key_filename}" /reset
   # Grant read-only access to current user
   icacls "{key_filename}" /grant:r "$($env:USERNAME):R"
   # Remove inheritance
   icacls "{key_filename}" /inheritance:r
   # Connect via SSH
   ssh -i "{key_filename}" ubuntu@{public_ip}

   macOS / Linux:
   chmod 400 {key_filename}
   ssh -i "{key_filename}" ubuntu@{public_ip}

Application Deployment:
- Expose your service on port 3000 and bind to 0.0.0.0.
- Verify at: {application_url}

Best regards,
Activity Coordination Team
"""

def create_message(sender_email, recipient_email, row):
    student_id = row["student_id"]
    full_name = row.get("full_name") or student_id
    instance_id = row["instance_id"]
    public_ip = row["public_ip"]
    public_dns = row["public_dns"]
    application_url = row["application_url"]
    key_path = Path(row["key_file_path"])
    key_filename = key_path.name

    msg = MIMEMultipart("mixed")
    msg["From"] = sender_email
    msg["To"] = recipient_email
    msg["Subject"] = f"[{student_id}] Your EC2 Connection Details & SSH Key (Backend Activity)"

    # Alternative body (text and html)
    body_alt = MIMEMultipart("alternative")

    text_part = MIMEText(
        EMAIL_TEXT_TEMPLATE.format(
            student_id=student_id,
            full_name=full_name,
            instance_id=instance_id,
            public_ip=public_ip,
            public_dns=public_dns,
            application_url=application_url,
            key_filename=key_filename,
        ),
        "plain",
    )
    html_part = MIMEText(
        EMAIL_HTML_TEMPLATE.format(
            student_id=student_id,
            full_name=full_name,
            instance_id=instance_id,
            public_ip=public_ip,
            public_dns=public_dns,
            application_url=application_url,
            key_filename=key_filename,
        ),
        "html",
    )

    body_alt.attach(text_part)
    body_alt.attach(html_part)
    msg.attach(body_alt)

    # Attach the private .pem key file
    if key_path.exists():
        with open(key_path, "rb") as attachment_file:
            part = MIMEBase("application", "x-pem-file")
            part.set_payload(attachment_file.read())
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f"attachment; filename={key_filename}",
        )
        msg.attach(part)
    else:
        print(f"[-] Warning: Key file not found at {key_path}")

    return msg

def main():
    parser = argparse.ArgumentParser(description="Send EC2 credentials & SSH keys to students via Email.")
    parser.add_argument("--dry-run", action="store_true", help="Print email preview without sending.")
    parser.add_argument("--target-student", type=str, help="Send only to a specific student_id (e.g. student-01).")
    args = parser.parse_args()

    if not config.INVENTORY_CSV.exists():
        print(f"[-] Error: {config.INVENTORY_CSV} does not exist. Run deploy_students.py first!")
        sys.exit(1)

    # Read Inventory
    students_data = []
    with open(config.INVENTORY_CSV, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if args.target_student and row["student_id"] != args.target_student:
                continue
            students_data.append(row)

    print(f"[+] Loaded {len(students_data)} recipient records.")

    if args.dry_run:
        print("\n" + "=" * 60)
        print("🔍 DRY-RUN MODE: Previewing First Email")
        print("=" * 60)
        sample = students_data[0]
        preview = EMAIL_TEXT_TEMPLATE.format(
            student_id=sample["student_id"],
            full_name=sample.get("full_name") or sample["student_id"],
            instance_id=sample["instance_id"],
            public_ip=sample["public_ip"],
            public_dns=sample["public_dns"],
            application_url=sample["application_url"],
            key_filename=Path(sample["key_file_path"]).name,
        )
        print(f"To: {sample['email']}")
        print(f"Subject: [{sample['student_id']}] Your EC2 Connection Details & SSH Key")
        print(f"Attached file: {sample['key_file_path']}")
        print("\nBody Preview:\n" + preview)
        print("=" * 60)
        print("Dry run completed. To send real emails, run without --dry-run.")
        return

    # SMTP Credentials
    smtp_server = config.SMTP_SERVER
    smtp_port = config.SMTP_PORT
    sender_email = config.SENDER_EMAIL
    smtp_username = config.SMTP_USERNAME or sender_email
    smtp_password = config.SMTP_PASSWORD

    if not sender_email or not smtp_password:
        print("\n[-] SMTP credentials are missing.")
        print("Please configure them via config.py or environment variables:")
        print("  set SENDER_EMAIL=your_email@gmail.com")
        print("  set SMTP_PASSWORD=your_app_password")
        print("  set SMTP_SERVER=smtp.gmail.com")
        print("  set SMTP_PORT=587")
        sys.exit(1)

    print(f"\n[+] Connecting to SMTP Server: {smtp_server}:{smtp_port}...")
    server = smtplib.SMTP(smtp_server, smtp_port)
    server.starttls()
    server.login(smtp_username, smtp_password)
    print("[+] Successfully authenticated with SMTP server.")

    success_count = 0
    fail_count = 0

    for idx, row in enumerate(students_data, start=1):
        recipient = row["email"]
        sid = row["student_id"]
        try:
            msg = create_message(sender_email, recipient, row)
            server.sendmail(sender_email, recipient, msg.as_string())
            print(f"[{idx}/{len(students_data)}] ✓ Sent to {sid} ({recipient})")
            success_count += 1
            time.sleep(0.5)  # Rate limiting
        except Exception as e:
            print(f"[{idx}/{len(students_data)}] ✗ Failed for {sid} ({recipient}): {e}")
            fail_count += 1

    server.quit()

    print("\n" + "=" * 60)
    print(f"Email Dispatch Complete! Sent: {success_count} | Failed: {fail_count}")
    print("=" * 60)

if __name__ == "__main__":
    main()
