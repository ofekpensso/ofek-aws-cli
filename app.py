import streamlit as st
import time
from utils import get_boto3_client, TAG_KEY, TAG_VALUE
ec2_client = get_boto3_client('ec2')
s3_client = get_boto3_client('s3')
r53_client = get_boto3_client('route53')
ssm_client = get_boto3_client('ssm')

# --- 1. Page Configuration (Tab title, icon, layout) ---
st.set_page_config(
    page_title="Ofek Cloud Manager",
    page_icon="☁️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. Sidebar Design ---
st.sidebar.title("🎮 Control Panel")
st.sidebar.markdown("---")

# Navigation Menu
menu = st.sidebar.radio(
    "Navigate to:",
    ["🏠 Dashboard", "🖥️ EC2 Instances", "📦 S3 Buckets", "🌐 Route53 Zones"]
)

st.sidebar.markdown("---")
st.sidebar.caption(f"Project: {TAG_VALUE}")
st.sidebar.caption("Status: Connected 🟢")

# --- 3. Main Content Area ---

# Header for all pages
st.title("☁️ Ofek Cloud Manager")
st.markdown("A secure interface for your AWS Walled Garden.")
st.divider()  # A visual line separator

# Logic for the "Dashboard" (Home Page)
if menu == "🏠 Dashboard":
    st.subheader("Welcome back, Ofek!")
    st.markdown("""
    This dashboard gives you full control over your cloud resources.

    ### 🚀 Quick Stats
    """)

    # Placeholder metrics (We will connect these to real data later)
    col1, col2, col3 = st.columns(3)
    col1.metric("Active Servers", "Loading...", "EC2")
    col2.metric("Storage Buckets", "Loading...", "S3")
    col3.metric("DNS Zones", "Loading...", "R53")

    st.info("👈 Choose a service from the sidebar to start managing.")

# ==========================================
#            STEP 2: EC2 MANAGER
# ==========================================
elif menu == "🖥️ EC2 Instances":
    st.header("🖥️ EC2 Instance Manager")

    # --- 1. Fetch Instances FIRST (Inventory Check) ---
    try:
        response = ec2_client.describe_instances(
            Filters=[{'Name': f'tag:{TAG_KEY}', 'Values': [TAG_VALUE]}]
        )

        instances = []
        active_count = 0

        for r in response['Reservations']:
            for i in r['Instances']:
                state = i['State']['Name']
                if state != "terminated":
                    active_count += 1

                name = "Unknown"
                if 'Tags' in i:
                    for t in i['Tags']:
                        if t['Key'] == 'Name':
                            name = t['Value']
                            break

                instances.append({
                    "id": i['InstanceId'],
                    "name": name,
                    "state": state,
                    "ip": i.get('PublicIpAddress', 'N/A'),
                    "type": i['InstanceType']
                })

    except Exception as e:
        st.error(f"Error loading instances: {e}")
        instances = []
        active_count = 0

    # --- 2. Launch New Instance Form (Smart & Dynamic) ---
    if active_count >= 2:
        st.warning(f"⚠️ Limit Reached: You have {active_count}/2 active instances. Terminate one to create a new one.")
    else:
        with st.expander(f"➕ Launch New Instance ({active_count}/2 Used)", expanded=True):
            col1, col2, col3 = st.columns(3)

            with col1:
                new_name = st.text_input("Instance Name", placeholder="web-server-1")

            with col2:
                os_type = st.selectbox("Operating System", ["Amazon Linux 2023", "Ubuntu 24.04 LTS"])

            with col3:
                inst_type = st.selectbox("Instance Type", ["t3.micro", "t2.small"])

            if st.button("🚀 Launch Instance"):
                if not new_name:
                    st.error("⚠️ Please enter a name for the instance.")
                else:
                    try:
                        # --- THE UPGRADE: Dynamic AMI Fetching ---
                        ami_id = None
                        with st.spinner(f"🔍 Fetching latest secure AMI for {os_type}..."):

                            if "Amazon Linux" in os_type:
                                # Method 1: Get latest from SSM Parameter Store (Best Practice)
                                param = ssm_client.get_parameter(
                                    Name='/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64'
                                )
                                ami_id = param['Parameter']['Value']

                            elif "Ubuntu" in os_type:
                                # Method 2: Search for latest image from Canonical
                                images = ec2_client.describe_images(
                                    Owners=['099720109477'],  # Canonical Owner ID
                                    Filters=[
                                        {'Name': 'name',
                                         'Values': ['ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*']},
                                        {'Name': 'architecture', 'Values': ['x86_64']},
                                        {'Name': 'state', 'Values': ['available']}
                                    ]
                                )
                                # Sort by creation date (Newest first)
                                sorted_imgs = sorted(images['Images'], key=lambda x: x['CreationDate'], reverse=True)
                                ami_id = sorted_imgs[0]['ImageId']

                        # --- Launch ---
                        with st.spinner(f"🚀 Launching {new_name} using {ami_id}..."):
                            ec2_client.run_instances(
                                ImageId=ami_id,
                                InstanceType=inst_type,
                                MinCount=1, MaxCount=1,
                                TagSpecifications=[{
                                    'ResourceType': 'instance',
                                    'Tags': [
                                        {'Key': 'Name', 'Value': new_name},
                                        {'Key': TAG_KEY, 'Value': TAG_VALUE},
                                        {'Key': 'Owner', 'Value': 'ofek'}
                                    ]
                                }]
                            )
                            st.success(f"✅ Instance '{new_name}' launched using latest AMI!")
                            time.sleep(2)
                            st.rerun()

                    except Exception as e:
                        st.error(f"❌ Error: {e}")

    st.divider()

    # --- 3. List & Control Instances ---
    st.subheader("Active Instances")

    if not instances:
        st.info("ℹ️ No managed instances found.")
    else:
        for inst in instances:
            if inst['state'] == "terminated": continue

            if inst['state'] == "running":
                status_color = "🟢"
            elif inst['state'] == "stopped":
                status_color = "🔴"
            else:
                status_color = "🟡"

            c1, c2, c3, c4, c5, c6 = st.columns([2, 2, 1.5, 1.5, 2, 2])

            c1.write(f"**{inst['name']}**")
            c2.caption(f"`{inst['id']}`")
            c3.write(f"{status_color} {inst['state'].upper()}")
            c4.caption(inst['type'])
            c5.code(inst['ip'])

            with c6:
                if inst['state'] == 'running':
                    if st.button("Stop", key=f"stop_{inst['id']}"):
                        ec2_client.stop_instances(InstanceIds=[inst['id']])
                        st.toast(f"🛑 Stopping {inst['name']}...")
                        time.sleep(1)
                        st.rerun()

                elif inst['state'] == 'stopped':
                    if st.button("Start", key=f"start_{inst['id']}"):
                        ec2_client.start_instances(InstanceIds=[inst['id']])
                        st.toast(f"🟢 Starting {inst['name']}...")
                        time.sleep(1)
                        st.rerun()

                if st.button("Terminate", key=f"term_{inst['id']}"):
                    ec2_client.terminate_instances(InstanceIds=[inst['id']])
                    st.toast(f"🗑️ Terminating {inst['name']}...")
                    time.sleep(1)
                    st.rerun()

            st.markdown("---")

elif menu == "📦 S3 Buckets":
    st.warning("🚧 S3 Manager - Coming in Step 3")

elif menu == "🌐 Route53 Zones":
    st.warning("🚧 Route53 Manager - Coming in Step 4")