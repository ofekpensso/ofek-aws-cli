# ☁️ OFEK-AWS-CLI

**A secure, compliant, and tag-based CLI tool for managing AWS resources.**

This tool allows users to manage the lifecycle of AWS resources (EC2, S3, Route53) within a strictly controlled environment. It enforces security best practices, cost management policies, and resource isolation using a "Walled Garden" approach based on tagging.

---

## 🚀 What This Tool Does

* **📊 Project Dashboard:** Instantly view all active resources (EC2, S3, Zones) created by the tool with a single command.
* **🖥️ EC2 Management:** Launches instances with strict constraints (Max 2 instances). Allowed types: `t3.micro` and `t2.small`. Automatically fetches the latest secure AMIs via SSM Parameter Store.
* **📦 S3 Storage:** Creates private, encrypted, version-enabled buckets by default. Supports optional **Public Buckets** via strict Bucket Policies.
* **🌐 Route53 DNS:** Manages Hosted Zones and DNS records. Includes **Idempotency** (prevents duplicate zones) and safety guardrails preventing the deletion of non-empty zones.
* **🔒 Resource Isolation:** Operates **only** on resources created by this tool (filtered by tags). It will never touch your other production resources.
* **☢️ Smart Cleanup:** Includes a "Nuke" feature to safely identify and delete all resources created by the CLI.

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
    git clone [https://github.com/ofekpensso/ofek-aws-cli.git](https://github.com/ofekpensso/ofek-aws-cli.git)
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
    This allows running `ofek-cli`, `ec2`, `s3`, and `route53` directly from the terminal.
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

### 🌐 Global Management (New!)
Manage the overall state of your project.

* **View Project Status (Inventory):**
    Displays a dashboard of all active EC2 instances, S3 buckets, and Route53 zones.
    ```bash
    ofek-cli status
    ```

* **Cleanup (The "Nuke" Command):**
    Safely scans and deletes ALL resources created by this tool. Includes a dry-run preview.
    ```bash
    ofek-cli cleanup
    ```

---

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
    # OR (Alias)
    ec2 delete i-0123456789abcdef0
    ```

### 2. S3 Operations (Storage)
Buckets are created with **Server-Side Encryption (AES-256)** and **Versioning** enabled by default.

* **Create a PRIVATE bucket (Default):**
    ```bash
    s3 create ofek-app-data-2026
    ```
* **Create a PUBLIC bucket:**
    ⚠️ **Warning:** This will attach a bucket policy allowing global read access.
    ```bash
    s3 create ofek-public-site --public
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
**Security:** Only IPs belonging to managed EC2 instances can be added to DNS records.

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


