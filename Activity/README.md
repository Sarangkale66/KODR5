# AWS Student Activity Fleet & Load Testing Automation

A complete, production-grade automation suite to deploy **50 EC2 instances** (`t3.medium`) with **individual unique SSH keys**, a **shared security group** (exposing port 22 & port 3000), an **automated email dispatch system** with `.pem` key attachments, a **dedicated aggressive load tester instance**, and a **complete teardown script**.

---

## 📁 Project Structure

```
Activity/
├── config.py                 # Central configurations (Region, instance types, tags, ports)
├── students.csv              # Student list (student_id, email)
├── deploy_students.py        # Provisions 50 EC2 instances with unique keys & shared SG
├── deploy_load_tester.py     # Provisions 1 large instance (c5.2xlarge) for load testing
├── run_load_test.py          # Asynchronous high-concurrency multi-target load generator
├── send_emails.py            # Automated email sender with attached .pem files
├── undeploy_all.py           # Complete teardown of all EC2 instances, SGs, and keys
├── keys/                     # (Auto-generated) Holds student-XX.pem private keys
├── students_inventory.csv    # (Auto-generated) Student-to-IP/DNS mapping
├── load_tester_info.json     # (Auto-generated) Load tester credentials & access
└── load_test_results.csv     # (Auto-generated) Benchmark results per student instance
```

---

## ⚙️ Prerequisites

1. **AWS CLI & Credentials**: Already configured in your terminal (`sarang_kale` in `ap-south-1`).
2. **Python Requirements**:
   ```powershell
   pip install boto3 aiohttp
   ```

---

## 🚀 Execution Workflow

### Step 1: Prepare Student List
Edit `students.csv` with your students' emails:
```csv
student_id,email
student-01,alice@example.com
student-02,bob@example.com
...
```

---

### Step 2: Deploy 50 Student Instances
Run the fleet provisioner:
```powershell
python deploy_students.py
```
**What this does:**
1. Creates the shared security group `student-lab-shared-sg` with **port 22** and **port 3000** inbound rules.
2. Dynamically generates **50 unique EC2 Key Pairs** and saves the `.pem` files in `./keys/`.
3. Launches 50 `t3.medium` instances in parallel using multi-threading.
4. Waits for all 50 instances to reach `running` state.
5. Queries their Public IP and Public DNS names and saves `students_inventory.csv` and `students_inventory.json`.

---

### Step 3: Send Connection Details & SSH Keys to Students
Set your email credentials (or configure them in `config.py`):
```powershell
$env:SENDER_EMAIL = "your_email@gmail.com"
$env:SMTP_PASSWORD = "your_google_app_password"
$env:SMTP_SERVER = "smtp.gmail.com"
$env:SMTP_PORT = "587"
```

1. **Test in Dry-Run Mode** (preview without sending):
   ```powershell
   python send_emails.py --dry-run
   ```

2. **Send test email to one specific student**:
   ```powershell
   python send_emails.py --target-student student-01
   ```

3. **Send to all 50 students**:
   ```powershell
   python send_emails.py
   ```
*Each student receives their Public IP, Public DNS, application URL (`http://<DNS>:3000/`), Windows/Linux SSH instructions (including `icacls` permission commands for Windows), and their distinct `.pem` key file attached directly to the email.*

---

### Step 4: Deploy the Dedicated Aggressive Load Tester
Launch the heavy compute instance for stress testing:
```powershell
python deploy_load_tester.py
```
**What this does:**
- Provisions a **`c5.2xlarge`** (8 vCPUs, 16 GiB RAM, up to 10 Gbps network) in the same AWS region and VPC.
- Attaches the shared security group.
- Automatically installs `python3`, `aiohttp`, `curl`, and `htop` via cloud-init UserData.
- Saves connection info to `load_tester_info.json`.

---

### Step 5: Execute Aggressive Load Testing

Aapke paas **2 options** hain:

#### Option A: Dedicated `c5.2xlarge` Instance se (Recommended for 50 Instances)
1. Load tester launch karein:
   ```powershell
   python deploy_load_tester.py
   ```
2. One-click remote blast engage karein:
   ```powershell
   python run_remote_load_test.py --mode crush --duration 30
   ```
   *Yeh script automatically `run_load_test.py` aur `students_inventory.csv` ko `c5.2xlarge` par upload karti hai aur AWS ke 10 Gbps network se 20,000+ RPS attack initiate karti hai.*

#### Option B: Local Machine se (Quick Test ke liye)
```powershell
python run_load_test.py --mode crush --duration 30
```

**Output:**
- Real-time progress.
- Aggregate throughput (Requests/sec), HTTP 2xx count vs errors/timeouts.
- Exports detailed per-student latency rankings (`p50`, `p90`, `p99`) to `load_test_results.csv`.

---

### Step 6: Full Teardown & Cleanup
When the activity concludes, wipe all resources to avoid any ongoing AWS charges:
```powershell
python undeploy_all.py
```
*(Or run `python undeploy_all.py --force` to skip confirmation).*

**What this cleans up:**
- Terminates all 50 student `t3.medium` instances and the `c5.2xlarge` load tester.
- Deletes all 50 unique AWS Key Pairs from EC2.
- Deletes the shared Security Group `student-lab-shared-sg`.
- Deletes all local `.pem` files in `./keys/`.


# Everything inside few scripts
```
python deploy_students.py
python send_emails.py
python deploy_load_tester.py
python run_remote_load_test.py --mode lethal --duration 30
python run_load_test.py
python undeploy_all.py
```

🛠️ Destructive Load Testing Commands (Aapke liye)

Aap jab students ki live class mein honge, toh ye commands run karke destructive load testing dikha sakte hain:

1. Quick Destructive Blast (Recommended for Live Demo)
powershell
```
   python run_load_test.py --mode crush --duration 30
```

What it does: 80 non-stop concurrent socket connections har student ke instance ko flood karte hain. Live dynamic dashboard terminal par chalta hai aur server choke hote hi 🔴 FAILING / 💀 CRASHED mark ho jata hai.

2. Maximum Destruction Blast (Single Instance Killer)
powershell```
   python run_load_test.py --workers-per-target 250 --duration 60 --timeout 1.0
```

What it does: 250 concurrent workers per student instance (~1,000+ requests/sec). Single t3.medium instance ki CPU 100% par lock ho jayegi, burst credits khatam honge aur server connection drop karna shuru karega.

3. Specific Path Attack (e.g. /api/data)

Agar students ka koi specific route hai:

powershell```
   python run_load_test.py --mode crush --path "/api/data" --duration 45
```