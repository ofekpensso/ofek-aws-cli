# ☁️ OFEK-AWS-CLI

**A secure, compliant, and tag-based CLI tool for managing AWS resources.**

This tool allows users to manage the lifecycle of AWS resources (EC2, S3, Route53) within a strictly controlled environment. It enforces security best practices, cost management policies, and resource isolation using a "Walled Garden" approach based on tagging.

---

## 🚀 What This Tool Does

* **EC2 Management:** Launches instances with strict constraints (Max 2 instances). Allowed types: `t3.micro` and `t2.small`. Automatically fetches the latest secure AMIs via SSM Parameter Store.
* **S3 Storage:** Creates private, encrypted, version-enabled buckets. Prevents accidental public exposure.
* **Route53 DNS:** Manages Hosted Zones and DNS records. Includes safety guardrails preventing the deletion of non-empty zones.
* **Resource Isolation:** Operates **only** on resources created by this tool (filtered by tags). It will never touch your other production resources.
* **Smart Cleanup:** Includes a "Nuke" feature to safely identify and delete all resources created by the CLI.

---

## 🛠️ Prerequisites

Before running the tool, ensure you have the following installed:

1.  **Python 3.8+**
2.  **AWS CLI** (Command Line Interface) - required for authentication setup.
    * [Download AWS CLI](https://aws.amazon.com/cli/)
3.  **AWS Credentials** configured locally (profile with permissions for EC2, S3, Route53, and SSM).
    * Run: `aws configure`
    * Or set env vars: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`

---

## 📦 Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/ofekpensso/ofek-aws-cli.git
    cd OFEK-AWS-CLI
    ```

2.  **Create a virtual environment (Recommended):**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Install as executable commands (Optional):**
    This allows running `ec2`, `s3`, and `route53` directly.
    ```bash
    pip install --editable .
    ```

---

## 🏷️ Tagging Convention

To ensure safety and isolation, every resource created by this tool is automatically tagged. The CLI **filters strictly** by these tags for all list/delete operations.

| Key | Value | Purpose |
| :--- | :--- | :--- |
| `CreatedBy` | `platform-cli` | Primary identifier for the "Walled Garden". |
| `Owner` | `ofek` | Identifies the resource owner. |
| `Project` | `cloud-course` | Context for billing/management. |

---

## 💻 Usage Examples

### 1. EC2 Operations (Compute)
The tool enforces a hard limit of **2 instances**.
Allowed types: `t3.micro`, `t2.small`.

* **Create a server:** (Auto-selects latest Amazon Linux 2023 via SSM)
    ```bash
    ec2 create --name my-web-server
    ```
* **Create an Ubuntu server:**
    ```bash
    ec2 create --name my-ubuntu-server --os ubuntu --type t2.small
    ```
* **List active instances:**
    ```bash
    ec2 list
    ```
* **Stop/Start an instance:**
    ```bash
    ec2 stop i-0123456789abcdef0
    ec2 start i-0123456789abcdef0
    ```
* **Terminate (Delete) an instance:**
    ```bash
    ec2 terminate i-0123456789abcdef0
    ```

### 2. S3 Operations (Storage)
Buckets are created with **Server-Side Encryption (AES-256)** and **Versioning** enabled by default.

* **Create a private bucket:**
    ```bash
    s3 create ofek-app-data-2026
    ```
* **Upload a file:**
    ```bash
    s3 upload ofek-app-data-2026 ./local-file.txt
    ```
* **List managed buckets:**
    ```bash
    s3 list
    ```
* **Delete a bucket:** (Forces deletion of all objects and versions inside)
    ```bash
    s3 delete ofek-app-data-2026
    ```

### 3. Route53 Operations (DNS)
Supports creating zones and managing `A` records (IP addresses).

* **Create a Hosted Zone:**
    ```bash
    route53 create-zone ofek-cloud.test.
    ```
* **Add/Update a DNS Record:**
    ```bash
    route53 add-record Z0123456789ABC api.ofek-cloud.test. 34.201.93.38
    ```
* **Delete a DNS Record:**
    ```bash
    route53 delete-record Z0123456789ABC api.ofek-cloud.test. 34.201.93.38
    ```
* **Delete a Zone:** (Includes safety check - Zone must be empty of custom records)
    ```bash
    route53 delete-zone Z0123456789ABC
    ```

---

## 🧹 Cleanup (The "Nuke" Command)

To prevent unnecessary costs, you can remove all resources created by this tool in one go.

**Features:**
* Scans all regions for resources tagged `CreatedBy=platform-cli`.
* Shows a "Dry Run" preview of resources to be deleted.
* Requires explicit confirmation.

**Run:**
```bash
python main.py cleanup


## 📸 Demo Evidence

Here is a visual walkthrough of the tool in action:

### 1. Creating & Managing Instances
![EC2 Creation](media/ec2-create.png)

### 2. Listing Active Resources (Table View)
![Resource List](media/s3cd.png)

### 3. Safety Cleanup (The "Nuke" Command)
![Cleanup Process](media/cleanup.png)

The following log demonstrates a full lifecycle run: creating resources (EC2, S3, Route53), verifying them, and performing a clean teardown using the `cleanup` command.

<details>
<summary><strong>Click to expand full terminal output log</strong> 📝</summary>

```text
(.venv) ofekpensso@MacBook-Air-sl-ofek OFEK-AWS-CLI % echo "This is proof for Ofek Project" > ofek-evidence.txt
(.venv) ofekpensso@MacBook-Air-sl-ofek OFEK-AWS-CLI % ec2 create --name ofek-cli-test
Finding latest AMI for amazon-linux...
Selected AMI: ami-0532be01f26a3de55
Launching instance 'ofek-cli-test'...
Success! Instance 'ofek-cli-test' (i-03a804ac8b4c88cba) created successfully.

(.venv) ofekpensso@MacBook-Air-sl-ofek OFEK-AWS-CLI % ec2 list
Fetching instances...
┏━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━┓
┃ Instance ID         ┃ Name          ┃ Type     ┃ State   ┃ Public IP     ┃
┡━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━┩
│ i-03a804ac8b4c88cba │ ofek-cli-test │ t3.micro │ running │ 18.206.212.67 │
└─────────────────────┴───────────────┴──────────┴─────────┴───────────────┘

(.venv) ofekpensso@MacBook-Air-sl-ofek OFEK-AWS-CLI % ec2 stop ofek-cli-test
Searching for instance named 'ofek-cli-test'...
Resolved ID: i-03a804ac8b4c88cba
Attempting to stop instance i-03a804ac8b4c88cba...
Success! Instance 'ofek-cli-test' (i-03a804ac8b4c88cba) is stopping...

(.venv) ofekpensso@MacBook-Air-sl-ofek OFEK-AWS-CLI % ec2 start ofek-cli-test
Searching for instance named 'ofek-cli-test'...
Resolved ID: i-03a804ac8b4c88cba
Attempting to start instance i-03a804ac8b4c88cba...
Success! Instance 'ofek-cli-test' (i-03a804ac8b4c88cba) is starting...

(.venv) ofekpensso@MacBook-Air-sl-ofek OFEK-AWS-CLI % s3 create ofek-cli-test
Creating bucket 'ofek-cli-test-3mbeag'...
Encryption enabled (AES256).
Bucket set to PRIVATE (Secure).
Success! Bucket 'ofek-cli-test-3mbeag' created.
Versioning enabled (Data Protection).

(.venv) ofekpensso@MacBook-Air-sl-ofek OFEK-AWS-CLI % s3 list
Fetching buckets (this might take a moment to scan tags)...
┏━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┓
┃ Bucket Name          ┃ Creation Date       ┃
┡━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━┩
│ ofek-cli-test-3mbeag │ 2026-02-03 14:16:17 │
└──────────────────────┴─────────────────────┘

(.venv) ofekpensso@MacBook-Air-sl-ofek OFEK-AWS-CLI % s3 upload  ofek-cli-test-3mbeag ofek-evidence.txt
Preparing to upload 'ofek-evidence.txt' to bucket 'ofek-cli-test-3mbeag'...
Success! File 'ofek-evidence.txt' uploaded to 'ofek-cli-test-3mbeag'.

(.venv) ofekpensso@MacBook-Air-sl-ofek OFEK-AWS-CLI % route53 create-zone ofek-cli.test.
Creating Hosted Zone for 'ofek-cli.test.'...
Success! Hosted Zone created.
Zone ID: Z04276643PMK993L88ASM
Name Servers: ns-318.awsdns-39.com, ns-848.awsdns-42.net, ns-1376.awsdns-44.org, ns-1989.awsdns-56.co.uk

(.venv) ofekpensso@MacBook-Air-sl-ofek OFEK-AWS-CLI % ec2 list
Fetching instances...
┏━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━┓
┃ Instance ID         ┃ Name          ┃ Type     ┃ State   ┃ Public IP     ┃
┡━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━┩
│ i-03a804ac8b4c88cba │ ofek-cli-test │ t3.micro │ running │ 174.129.52.15 │
└─────────────────────┴───────────────┴──────────┴─────────┴───────────────┘

(.venv) ofekpensso@MacBook-Air-sl-ofek OFEK-AWS-CLI % route53 add-record Z04276643PMK993L88ASM api.ofek-cli.test. 174.129.52.15
Success! Record 'api.ofek-cli.test.' -> 174.129.52.15 set.

(.venv) ofekpensso@MacBook-Air-sl-ofek OFEK-AWS-CLI % route53 list-records Z04276643PMK993L88ASM
┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Name               ┃ Type ┃ Value                                                                         ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ ofek-cli.test.     │ NS   │ ns-318.awsdns-39.com., ns-848.awsdns-42.net., ns-1376.awsdns-44.org.,         │
│                    │      │ ns-1989.awsdns-56.co.uk.                                                      │
│ ofek-cli.test.     │ SOA  │ ns-318.awsdns-39.com. awsdns-hostmaster.amazon.com. 1 7200 900 1209600 86400  │
│ api.ofek-cli.test. │ A    │ 174.129.52.15                                                                 │
└────────────────────┴──────┴───────────────────────────────────────────────────────────────────────────────┘

(.venv) ofekpensso@MacBook-Air-sl-ofek OFEK-AWS-CLI % ofek-cli cleanup
Scanning for resources to delete...

Found 3 resources managed by platform-cli:

[EC2 Instances] (1)
 - i-03a804ac8b4c88cba (ofek-cli-test)

[S3 Buckets] (1)
 - ofek-cli-test-3mbeag

[Route53 Zones] (1)
 - ofek-cli.test. (Z04276643PMK993L88ASM)

⚠️  Are you sure you want to PERMANENTLY DELETE these resources? [y/N]: y

--- Starting Cleanup ---
Scanning for EC2 instances to terminate...
Resolved ID: i-03a804ac8b4c88cba
Attempting to terminate instance i-03a804ac8b4c88cba...
Success! Instance 'i-03a804ac8b4c88cba' (i-03a804ac8b4c88cba) is being terminated.
Scanning for S3 buckets to delete (this might take a moment)...
Deleting bucket ofek-cli-test-3mbeag...
Deleted ofek-cli-test-3mbeag
Scanning for Route53 Zones to delete...
Cleaning up Zone: ofek-cli.test. (Z04276643PMK993L88ASM)...
 - Deleted 1 records.
 - Zone deleted.

Cleanup complete! 🧹