# ☁️ OFEK-AWS-CLI & Cloud Manager

**A secure, compliant, and tag-based tool for managing AWS resources via CLI or Web UI.**

This tool allows users to manage the lifecycle of AWS resources (EC2, S3, Route53) within a strictly controlled environment. It enforces security best practices, cost management policies, and resource isolation using a "Walled Garden" approach based on tagging.

You can interact with the cloud using a robust **Terminal CLI** or a modern **Web Dashboard**.

---

## 🚀 Key Features

* **🖥️ Hybrid Interface:** Choose between a fast Command Line Interface (CLI) or a visual Web Dashboard (UI).
* **📊 Visual Dashboard:** Real-time metrics, resource inventory, and status monitoring in a browser-based UI.
* **💻 EC2 Management:** Launch instances with strict constraints (Max 2 instances). Allowed types: `t3.micro` and `t2.small`. Automatically fetches the latest secure AMIs via SSM.
* **📦 S3 Storage:**
    * **CLI:** Command-based creation and uploads.
    * **UI:** Drag-and-drop file uploads, visual file listing, and one-click bucket creation.
    * **Security:** Private, encrypted (AES-256), and versioned by default.
* **🌐 Route53 DNS:** Manage Hosted Zones and DNS records visually or via commands. Includes idempotency checks.
* **🔒 Resource Isolation:** Operates **only** on resources created by this tool (filtered by tags). It will never touch your other production resources.
* **☢️ Smart Cleanup:** Includes a "Nuke" feature (in both CLI and UI) to safely identify and delete all resources created by the tool.

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

1. **Clone the repository:**
~~~bash
git clone https://github.com/ofekpensso/ofek-aws-cli.git
cd OFEK-AWS-CLI
~~~

2. **Set up a Virtual Environment (Recommended):**
Using a virtual environment ensures your project dependencies are isolated.
* **Create the environment:**
~~~bash
python -m venv .venv
~~~
* **Activate it:**
    * **Mac / Linux:** `source .venv/bin/activate`
    * **Windows:** `.venv\Scripts\activate`

3. **Install dependencies:**
~~~bash
pip install -r requirements.txt
~~~

4. **Install as executable commands:**
This allows you to run `ofek-cli`, `ec2`, `s3`, and `route53` directly from your terminal.
~~~bash
pip install --editable .
~~~

---

## 🏷️ Tagging Convention

To ensure safety and isolation, every resource created by this tool is automatically tagged. The tool **filters strictly** by these tags for all list/delete operations.

| Key | Value | Purpose |
| :--- | :--- | :--- |
| `CreatedBy` | `platform-cli` | Primary identifier for the "Walled Garden". |
| `Owner` | `ofek` | Identifies the resource owner. |
| `Project` | `cloud-course` | Context for billing/management. |

---

## 💻 Usage: Web UI (Visual)

The easiest way to manage your resources is via the Dashboard.

**Run the Dashboard:**
~~~bash
streamlit run app.py
~~~
This will automatically open `http://localhost:8501` in your browser.

**UI Features:**
* **Dashboard:** View total active resources and health status.
* **EC2:** Launch new servers with a simple form; Stop/Terminate with one click.
* **S3:** Create buckets and upload files using a drag-and-drop interface.
* **Route53:** Create hosted zones, manage DNS records (A-Records), and visualize zone details.
* **Danger Zone:** A "Nuke System" button to delete everything (requires confirmation).

---

## ⌨️ Usage: CLI (Terminal)

For advanced users who prefer the command line.

### 🌐 Global Management
* **View Project Status (Inventory):**
    Displays a dashboard of all active EC2 instances, S3 buckets, and Route53 zones.
    ~~~bash
    ofek-cli status
    ~~~

* **Cleanup (The "Nuke" Command):**
    Safely scans and deletes ALL resources created by this tool. Includes a dry-run preview.
    ~~~bash
    ofek-cli cleanup
    ~~~

### 1. EC2 Operations (Compute)
The tool enforces a hard limit of **2 instances**.
Allowed types: `t3.micro`, `t2.small`.

* **Create a server:** (Auto-selects latest Amazon Linux 2023 via SSM)
    ~~~bash
    ec2 create --name <YOUR_SERVER_NAME>
    ~~~
* **Create an Ubuntu server:**
    ~~~bash
    ec2 create --name <YOUR_SERVER_NAME> --os ubuntu --type t2.small
    ~~~
* **List active instances:**
    ~~~bash
    ec2 list
    ~~~

* **Stop an instance:**
~~~bash
ec2 stop <INSTANCE_NAME_OR_ID>
~~~

* **Start an instance:**
~~~bash
ec2 start <INSTANCE_NAME_OR_ID>
~~~

* **Terminate an instance:**
~~~bash
ec2 terminate <INSTANCE_NAME_OR_ID>
ec2 delete <INSTANCE_NAME_OR_ID>
~~~

### 2. S3 Operations (Storage)
Buckets are created with **Server-Side Encryption (AES-256)** and **Versioning** enabled by default.

* **Create a PRIVATE bucket (Default):**
    ~~~bash
    s3 create <BUCKET_NAME>
    ~~~
* **Create a PUBLIC bucket:**
    ⚠️ **Warning:** This will attach a bucket policy allowing global read access.
    ~~~bash
    s3 create <BUCKET_NAME> --public
    ~~~
* **Upload a file:**
    ~~~bash
    s3 upload <BUCKET_NAME> <PATH_TO_FILE>
    ~~~
* **List managed buckets:**
    ~~~bash
    s3 list
    ~~~
* **Delete a bucket:** (Forces deletion of all objects and versions inside)
    ~~~bash
    s3 delete <BUCKET_NAME>
    ~~~

### 3. Route53 Operations (DNS)
Supports creating zones and managing `A` records (IP addresses).
**Security:** Only IPs belonging to managed EC2 instances can be added to DNS records.

* **Create a Hosted Zone:**
    ~~~bash
    route53 create-zone <DOMAIN_NAME>
    ~~~
    *Example: `route53 create-zone my-app.test.`*

* **Add/Update a DNS Record:**
    ~~~bash
    route53 add-record <ZONE_ID> <FULL_RECORD_NAME> <IP_ADDRESS>
    ~~~
    *Example: `route53 add-record Z0123... api.my-app.test. 34.200.10.10`*

* **Delete a DNS Record:**
    ~~~bash
    route53 delete-record <ZONE_ID> <FULL_RECORD_NAME> <IP_ADDRESS>
    ~~~

* **Delete a Zone:** (Includes safety check - Zone must be empty of custom records)
    ~~~bash
    route53 delete-zone <ZONE_ID>
    ~~~