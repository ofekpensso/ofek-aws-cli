import streamlit as st
import time
from utils import get_boto3_client, TAG_KEY, TAG_VALUE
import json

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

# ==========================================
#            STEP 3: S3 MANAGER
# ==========================================
elif menu == "📦 S3 Buckets":
    st.header("📦 S3 Bucket Manager")

    # --- 1. Create New Bucket Form ---
    with st.expander("➕ Create New Bucket"):
        col1, col2 = st.columns([3, 1])

        with col1:
            b_name = st.text_input("Bucket Name (Unique)", placeholder="my-app-data-2026")

        with col2:
            st.write("")
            st.write("")
            is_public = st.checkbox("Make Public? ⚠️")

        if is_public:
            st.warning("⚠️ Warning: This will make all files in the bucket accessible to the world!")

        if st.button("Create Bucket"):
            if not b_name:
                st.error("Please enter a bucket name.")
            else:
                try:
                    with st.spinner("Creating bucket..."):
                        s3_client.create_bucket(Bucket=b_name)
                        s3_client.get_waiter('bucket_exists').wait(Bucket=b_name)

                        # Tags & Security
                        s3_client.put_bucket_tagging(
                            Bucket=b_name,
                            Tagging={'TagSet': [{'Key': TAG_KEY, 'Value': TAG_VALUE}]}
                        )
                        s3_client.put_bucket_encryption(
                            Bucket=b_name,
                            ServerSideEncryptionConfiguration={
                                'Rules': [{'ApplyServerSideEncryptionByDefault': {'SSEAlgorithm': 'AES256'}}]
                            }
                        )
                        s3_client.put_bucket_versioning(
                            Bucket=b_name,
                            VersioningConfiguration={'Status': 'Enabled'}
                        )

                        if is_public:
                            s3_client.delete_public_access_block(Bucket=b_name)
                            bucket_policy = {
                                "Version": "2012-10-17",
                                "Statement": [{
                                    "Sid": "PublicReadGetObject",
                                    "Effect": "Allow",
                                    "Principal": "*",
                                    "Action": "s3:GetObject",
                                    "Resource": f"arn:aws:s3:::{b_name}/*"
                                }]
                            }
                            s3_client.put_bucket_policy(Bucket=b_name, Policy=json.dumps(bucket_policy))
                            st.success(f"✅ Public Bucket '{b_name}' created!")
                        else:
                            s3_client.put_public_access_block(
                                Bucket=b_name,
                                PublicAccessBlockConfiguration={
                                    'BlockPublicAcls': True, 'IgnorePublicAcls': True,
                                    'BlockPublicPolicy': True, 'RestrictPublicBuckets': True
                                }
                            )
                            st.success(f"✅ Private Bucket '{b_name}' created!")

                        time.sleep(1)
                        st.rerun()

                except Exception as e:
                    st.error(f"❌ Error: {e}")

    st.divider()

    # --- 2. List & Manage Buckets ---
    st.subheader("Your Buckets")

    with st.spinner("Scanning buckets..."):
        try:
            response = s3_client.list_buckets()
            managed_buckets = []

            # Filter Buckets
            for b in response['Buckets']:
                try:
                    tags = s3_client.get_bucket_tagging(Bucket=b['Name'])
                    for t in tags['TagSet']:
                        if t['Key'] == TAG_KEY and t['Value'] == TAG_VALUE:
                            managed_buckets.append(b['Name'])
                            break
                except Exception:
                    continue

            if not managed_buckets:
                st.info("ℹ️ No managed buckets found.")
            else:
                for bucket_name in managed_buckets:
                    # Layout
                    c1, c2, c3 = st.columns([3, 2, 1.5])

                    c1.write(f"📦 **{bucket_name}**")

                    # Status Check
                    try:
                        pab = s3_client.get_public_access_block(Bucket=bucket_name)
                        is_secure = pab['PublicAccessBlockConfiguration']['BlockPublicPolicy']
                        status_text = "🔒 Private" if is_secure else "🌍 Public"
                        status_color = "green" if is_secure else "red"
                    except:
                        status_text = "🌍 Public (No Block)"
                        status_color = "red"

                    c2.markdown(f":{status_color}[{status_text}]")

                    # --- SAFE DELETE LOGIC ---
                    # 1. The main delete button
                    if c3.button("Delete", key=f"pre_del_{bucket_name}"):
                        # Check contents first
                        objs = s3_client.list_objects_v2(Bucket=bucket_name)
                        file_count = len(objs.get('Contents', []))

                        if file_count == 0:
                            # Empty? Delete immediately
                            s3_client.delete_bucket(Bucket=bucket_name)
                            st.toast(f"🗑️ Deleted {bucket_name}")
                            time.sleep(1)
                            st.rerun()
                        else:
                            # Not empty? Trigger confirmation mode
                            st.session_state[f"confirm_delete_{bucket_name}"] = True

                    # 2. The Confirmation Warning (Only appears if triggered)
                    if st.session_state.get(f"confirm_delete_{bucket_name}"):
                        st.error(f"⚠️ Warning: Bucket contains files! Are you sure?")
                        col_confirm, col_cancel = st.columns(2)

                        if col_confirm.button("Yes, Delete Everything", key=f"force_del_{bucket_name}"):
                            try:
                                with st.spinner(f"Nuking {bucket_name}..."):
                                    # Recursive Delete
                                    objects = s3_client.list_objects_v2(Bucket=bucket_name)
                                    if 'Contents' in objects:
                                        for obj in objects['Contents']:
                                            s3_client.delete_object(Bucket=bucket_name, Key=obj['Key'])

                                    # Versions
                                    versions = s3_client.list_object_versions(Bucket=bucket_name)
                                    if 'Versions' in versions:
                                        for v in versions['Versions']:
                                            s3_client.delete_object(Bucket=bucket_name, Key=v['Key'],
                                                                    VersionId=v['VersionId'])
                                    if 'DeleteMarkers' in versions:
                                        for dm in versions['DeleteMarkers']:
                                            s3_client.delete_object(Bucket=bucket_name, Key=dm['Key'],
                                                                    VersionId=dm['VersionId'])

                                    s3_client.delete_bucket(Bucket=bucket_name)
                                    st.success(f"🗑️ Deleted {bucket_name}")
                                    # Clear state
                                    del st.session_state[f"confirm_delete_{bucket_name}"]
                                    time.sleep(1)
                                    st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")

                        if col_cancel.button("Cancel", key=f"cancel_{bucket_name}"):
                            del st.session_state[f"confirm_delete_{bucket_name}"]
                            st.rerun()

                    # --- EXPANDER: Upload & File List ---
                    with st.expander(f"📂 Manage Files in '{bucket_name}'"):

                        # --- UPLOAD SECTION (Auto-Clear) ---
                        # Initialize session state for uploader key if not exists
                        if f"uploader_key_{bucket_name}" not in st.session_state:
                            st.session_state[f"uploader_key_{bucket_name}"] = 0

                        # Dynamic key allows us to reset the widget
                        dynamic_key = f"up_{bucket_name}_{st.session_state[f'uploader_key_{bucket_name}']}"

                        uploaded_file = st.file_uploader("Upload File", key=dynamic_key)

                        if uploaded_file is not None:
                            if st.button("Start Upload", key=f"btn_up_{bucket_name}"):
                                try:
                                    with st.spinner("Uploading..."):
                                        s3_client.upload_fileobj(uploaded_file, bucket_name, uploaded_file.name)
                                        st.success(f"✅ '{uploaded_file.name}' uploaded!")

                                        # Increment key to reset uploader on next run
                                        st.session_state[f"uploader_key_{bucket_name}"] += 1
                                        time.sleep(1)
                                        st.rerun()
                                except Exception as e:
                                    st.error(f"Upload failed: {e}")

                        st.markdown("---")

                        # --- FILE LIST ---
                        st.caption("Current Files:")
                        try:
                            objs = s3_client.list_objects_v2(Bucket=bucket_name)
                            if 'Contents' in objs:
                                for obj in objs['Contents']:
                                    size_kb = round(obj['Size'] / 1024, 2)
                                    st.text(f"📄 {obj['Key']}  ({size_kb} KB)")
                            else:
                                st.info("Bucket is empty.")
                        except Exception as e:
                            st.error(f"Could not list files: {e}")

                    st.markdown("---")

        except Exception as e:
            st.error(f"Error loading buckets: {e}")

# ==========================================
#            STEP 4: ROUTE53 MANAGER
# ==========================================
elif menu == "🌐 Route53 Zones":
    st.header("🌐 Route53 DNS Manager")

    # --- 1. Create Zone Form ---
    with st.expander("➕ Create Hosted Zone"):
        domain = st.text_input("Domain Name (e.g., myapp.test)", placeholder="myapp.test")

        if st.button("Create Zone"):
            if not domain:
                st.error("Enter a domain name.")
            else:
                try:
                    # Ensure trailing dot
                    if not domain.endswith('.'): domain += '.'

                    ref = str(time.time())  # Unique reference
                    res = r53_client.create_hosted_zone(
                        Name=domain,
                        CallerReference=ref,
                        HostedZoneConfig={'Comment': 'Created via Ofek UI'}
                    )
                    zone_id = res['HostedZone']['Id'].split('/')[-1]

                    # Apply Walled Garden Tags
                    r53_client.change_tags_for_resource(
                        ResourceType='hostedzone',
                        ResourceId=zone_id,
                        AddTags=[{'Key': TAG_KEY, 'Value': TAG_VALUE}]
                    )
                    st.success(f"✅ Zone '{domain}' created successfully!")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    st.divider()

    # --- 2. List & Manage Zones ---
    st.subheader("Managed Zones")

    with st.spinner("Filtering zones..."):
        try:
            all_zones = r53_client.list_hosted_zones()['HostedZones']
            managed_zones = []

            # Filter by Tag
            for z in all_zones:
                try:
                    z_id = z['Id'].split('/')[-1]
                    tags_response = r53_client.list_tags_for_resource(ResourceType='hostedzone', ResourceId=z_id)
                    tag_list = tags_response['ResourceTagSet']['Tags']

                    for t in tag_list:
                        if t['Key'] == TAG_KEY and t['Value'] == TAG_VALUE:
                            managed_zones.append(z)
                            break
                except Exception:
                    continue

            if not managed_zones:
                st.info("ℹ️ No managed zones found.")
            else:
                for z in managed_zones:
                    z_id = z['Id'].split('/')[-1]
                    z_name = z['Name']

                    # --- Zone Header ---
                    c1, c2, c3 = st.columns([3, 2, 1])
                    c1.write(f"🌐 **{z_name}**")
                    c2.caption(f"`{z_id}`")

                    if c3.button("Delete Zone", key=f"del_zone_{z_id}"):
                        try:
                            r53_client.delete_hosted_zone(Id=z_id)
                            st.success("Zone deleted!")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error("❌ Zone must be empty of custom records before deleting.")

                    # --- DETAILS EXPANDER (Records Manager) ---
                    with st.expander(f"📝 Manage Records for {z_name}"):

                        # A. Add New Record Form
                        st.caption("Add 'A' Record (Connect Domain to IP)")
                        rc1, rc2, rc3 = st.columns([2, 2, 1])
                        with rc1:
                            sub_name = st.text_input("Subdomain (e.g. www)", key=f"sub_{z_id}")
                        with rc2:
                            target_ip = st.text_input("Target IP Address", key=f"ip_{z_id}")
                        with rc3:
                            st.write("")
                            st.write("")
                            if st.button("Add", key=f"add_rec_{z_id}"):
                                full_name = f"{sub_name}.{z_name}" if sub_name else z_name
                                try:
                                    r53_client.change_resource_record_sets(
                                        HostedZoneId=z_id,
                                        ChangeBatch={
                                            'Changes': [{
                                                'Action': 'UPSERT',
                                                'ResourceRecordSet': {
                                                    'Name': full_name,
                                                    'Type': 'A',
                                                    'TTL': 300,
                                                    'ResourceRecords': [{'Value': target_ip}]
                                                }
                                            }]
                                        }
                                    )
                                    st.success(f"✅ Record {full_name} -> {target_ip} added!")
                                    time.sleep(1)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {e}")

                        st.markdown("---")

                        # B. List Existing Records
                        st.caption("Current DNS Records:")
                        try:
                            records = r53_client.list_resource_record_sets(HostedZoneId=z_id)['ResourceRecordSets']

                            for rec in records:
                                # Skip default SOA/NS records to keep UI clean? (Optional, currently showing all)
                                rec_name = rec['Name']
                                rec_type = rec['Type']
                                rec_values = [r['Value'] for r in rec.get('ResourceRecords', [])]
                                value_str = ", ".join(rec_values)

                                # Display Row
                                r_col1, r_col2, r_col3, r_col4 = st.columns([3, 1, 3, 1])
                                r_col1.write(f"`{rec_name}`")
                                r_col2.write(f"**{rec_type}**")
                                r_col3.write(value_str)

                                # Delete Record Button (Only for non-SOA/NS)
                                if rec_type not in ['SOA', 'NS']:
                                    if r_col4.button("🗑️", key=f"del_rec_{rec_name}_{z_id}"):
                                        try:
                                            r53_client.change_resource_record_sets(
                                                HostedZoneId=z_id,
                                                ChangeBatch={
                                                    'Changes': [{
                                                        'Action': 'DELETE',
                                                        'ResourceRecordSet': rec
                                                    }]
                                                }
                                            )
                                            st.toast(f"Deleted {rec_name}")
                                            time.sleep(1)
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"Error: {e}")
                                else:
                                    r_col4.write("🔒")  # Lock icon for default records

                        except Exception as e:
                            st.error(f"Could not load records: {e}")

                    st.markdown("---")

        except Exception as e:
            st.error(f"Error loading zones: {e}")