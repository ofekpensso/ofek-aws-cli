import streamlit as st
import time
# Import connection logic and constants from your existing utils.py
from utils import get_boto3_client, TAG_KEY, TAG_VALUE

# --- Page Configuration ---
st.set_page_config(page_title="Ofek AWS Manager", page_icon="☁️", layout="wide")

st.title("☁️ Ofek Cloud Manager")
st.markdown("### Control Panel for EC2, S3, and Route53")

# --- Sidebar Navigation ---
menu = st.sidebar.radio("Select Service", ["🖥️ EC2 Instances", "📦 S3 Buckets", "🌐 Route53 Zones"])

# --- Initialize AWS Clients using utils.py ---
ec2_client = get_boto3_client('ec2')
s3_client = get_boto3_client('s3')
r53_client = get_boto3_client('route53')

# ==========================================
#               EC2 SECTION
# ==========================================
if menu == "🖥️ EC2 Instances":
    st.header("EC2 Instance Manager")

    # --- Launch New Instance Form ---
    with st.expander("➕ Launch New Instance"):
        col1, col2 = st.columns(2)
        with col1:
            new_name = st.text_input("Instance Name", placeholder="web-server-1")
        with col2:
            os_type = st.selectbox("Operating System", ["amazon-linux", "ubuntu"])

        if st.button("Launch Instance"):
            if not new_name:
                st.error("Please enter a name!")
            else:
                try:
                    with st.spinner('Launching...'):
                        # AMI Logic (Same as in your CLI)
                        ami_id = "ami-0532be01f26a3de55" if os_type == "amazon-linux" else "ami-04b4f1a9cf54c11d0"

                        ec2_client.run_instances(
                            ImageId=ami_id,
                            InstanceType='t3.micro',
                            MinCount=1, MaxCount=1,
                            TagSpecifications=[{
                                'ResourceType': 'instance',
                                'Tags': [{'Key': 'Name', 'Value': new_name}, {'Key': TAG_KEY, 'Value': TAG_VALUE}]
                            }]
                        )
                        st.success(f"Instance '{new_name}' launched! Refreshing...")
                        time.sleep(2)
                        st.rerun()  # Refresh page
                except Exception as e:
                    st.error(f"Error: {e}")

    # --- List Active Instances ---
    st.subheader("Active Instances")
    try:
        # Filter instances by our specific project tag
        response = ec2_client.describe_instances(Filters=[{'Name': f'tag:{TAG_KEY}', 'Values': [TAG_VALUE]}])
        instances = []
        for r in response['Reservations']:
            for i in r['Instances']:
                # Extract Name tag safely
                name = next((tag['Value'] for tag in i.get('Tags', []) if tag['Key'] == 'Name'), "Unknown")
                state = i['State']['Name']
                public_ip = i.get('PublicIpAddress', 'N/A')
                instances.append({"ID": i['InstanceId'], "Name": name, "State": state, "IP": public_ip})

        if not instances:
            st.info("No instances found.")
        else:
            # Render a custom row for each instance
            for inst in instances:
                c1, c2, c3, c4, c5 = st.columns([2, 2, 1, 2, 2])
                c1.write(f"**{inst['Name']}**")
                c2.write(f"`{inst['ID']}`")

                # Visual indicator for state
                state_color = "🟢" if inst['State'] == "running" else "🔴"
                c3.write(f"{state_color} {inst['State']}")
                c4.write(inst['IP'])

                # Action Buttons
                if inst['State'] == 'running':
                    if c5.button("Stop", key=f"stop_{inst['ID']}"):
                        ec2_client.stop_instances(InstanceIds=[inst['ID']])
                        st.toast(f"Stopping {inst['Name']}...")
                        time.sleep(1)
                        st.rerun()

                # Terminate Button (Always visible)
                if c5.button("Terminate", key=f"term_{inst['ID']}"):
                    ec2_client.terminate_instances(InstanceIds=[inst['ID']])
                    st.warning(f"Terminating {inst['Name']}...")
                    time.sleep(1)
                    st.rerun()

    except Exception as e:
        st.error(f"Failed to load instances: {e}")

# ==========================================
#               S3 SECTION
# ==========================================
elif menu == "📦 S3 Buckets":
    st.header("S3 Bucket Manager")

    # --- Create Bucket Form ---
    with st.expander("➕ Create New Bucket"):
        b_name = st.text_input("Bucket Name (Must be unique globally)", placeholder="ofek-ui-test")
        is_public = st.checkbox("Make Public? (⚠️ DANGER)")

        if st.button("Create Bucket"):
            if not b_name:
                st.error("Please enter a bucket name.")
            else:
                try:
                    # Create Bucket
                    s3_client.create_bucket(Bucket=b_name)
                    # Add Tags (Walled Garden)
                    s3_client.put_bucket_tagging(Bucket=b_name,
                                                 Tagging={'TagSet': [{'Key': TAG_KEY, 'Value': TAG_VALUE}]})

                    if not is_public:
                        # Apply Public Access Block (Private)
                        s3_client.put_public_access_block(
                            Bucket=b_name,
                            PublicAccessBlockConfiguration={
                                'BlockPublicAcls': True, 'IgnorePublicAcls': True,
                                'BlockPublicPolicy': True, 'RestrictPublicBuckets': True
                            }
                        )
                        st.success("Private Bucket created successfully!")
                    else:
                        st.warning("Public Bucket created!")

                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"AWS Error: {e}")

    # --- List Managed Buckets ---
    st.subheader("Your Buckets")
    try:
        response = s3_client.list_buckets()
        managed_buckets = []

        # Filter buckets manually by checking tags (S3 list_buckets doesn't support tag filtering directly)
        for b in response['Buckets']:
            try:
                tags = s3_client.get_bucket_tagging(Bucket=b['Name'])
                for t in tags['TagSet']:
                    if t['Key'] == TAG_KEY and t['Value'] == TAG_VALUE:
                        managed_buckets.append(b['Name'])
                        break
            except:
                continue  # Skip buckets with no tags or permission issues

        if not managed_buckets:
            st.info("No managed buckets found.")
        else:
            for bucket in managed_buckets:
                c1, c2 = st.columns([4, 1])
                c1.write(f"📦 {bucket}")

                # Delete Button
                if c2.button("Delete", key=f"del_{bucket}"):
                    try:
                        # Recursive Delete: Empty bucket first
                        objects = s3_client.list_objects_v2(Bucket=bucket)
                        if 'Contents' in objects:
                            for obj in objects['Contents']:
                                s3_client.delete_object(Bucket=bucket, Key=obj['Key'])

                        # Now delete the bucket itself
                        s3_client.delete_bucket(Bucket=bucket)
                        st.success(f"Deleted {bucket}")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error deleting bucket: {e}")

    except Exception as e:
        st.error(f"Could not load buckets: {e}")

# ==========================================
#            ROUTE53 SECTION
# ==========================================
elif menu == "🌐 Route53 Zones":
    st.header("DNS Zone Manager")

    # --- Create Zone Form ---
    with st.expander("➕ Create Hosted Zone"):
        domain = st.text_input("Domain Name", placeholder="myapp.test.")
        if st.button("Create Zone"):
            if not domain:
                st.error("Enter a domain name.")
            else:
                try:
                    ref = str(time.time())  # Unique reference
                    res = r53_client.create_hosted_zone(
                        Name=domain,
                        CallerReference=ref,
                        HostedZoneConfig={'Comment': 'Created via Ofek UI'}
                    )
                    zone_id = res['HostedZone']['Id'].split('/')[-1]

                    # Add Tags
                    r53_client.change_tags_for_resource(
                        ResourceType='hostedzone',
                        ResourceId=zone_id,
                        AddTags=[{'Key': TAG_KEY, 'Value': TAG_VALUE}]
                    )
                    st.success(f"Zone created: {zone_id}")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    # --- List Zones ---
    st.subheader("Managed Zones")
    try:
        zones = r53_client.list_hosted_zones()['HostedZones']

        has_zones = False
        for z in zones:
            # Basic display logic (In production, we should filter by tags here too)
            c1, c2, c3 = st.columns([3, 2, 1])
            c1.write(f"🌐 **{z['Name']}**")
            c2.write(f"`{z['Id'].split('/')[-1]}`")

            if c3.button("Delete", key=z['Id']):
                try:
                    r53_client.delete_hosted_zone(Id=z['Id'])
                    st.success("Zone deleted!")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error("Error: Zone must be empty to delete.")
            has_zones = True

        if not has_zones:
            st.info("No hosted zones found.")

    except Exception as e:
        st.error(f"Error loading zones: {e}")

# --- Footer ---
st.sidebar.markdown("---")
st.sidebar.caption("Built with Python & Streamlit 🚀")