import click
from utils import get_boto3_resource, get_common_tags, TAG_KEY, TAG_VALUE
from rich.console import Console
from rich.table import Table

ec2 = get_boto3_resource('ec2')


def get_latest_ami(os_type):
    """
    Fetches the latest AMI ID for Ubuntu or Amazon Linux 2.
    It filters images by owner and name, then sorts by creation date.
    """
    if os_type == "ubuntu":
        # Filter for Ubuntu 22.04 LTS
        filters = [{'Name': 'name', 'Values': ['ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*']}]
        owner = '099720109477'  # Canonical (Official Ubuntu Owner ID)
    else:
        # Filter for Amazon Linux 2
        filters = [{'Name': 'name', 'Values': ['amzn2-ami-hvm-*-x86_64-gp2']}]
        owner = '137112412989'  # Amazon (Official Owner ID)

    # Fetch images from AWS
    images = list(ec2.images.filter(Owners=[owner], Filters=filters))

    if not images:
        raise Exception(f"Could not find AMI for {os_type}")

    # Sort by creation date (descending) to get the newest one
    images.sort(key=lambda x: x.creation_date, reverse=True)

    return images[0].id


def count_our_instances():
    """
    Counts how many running instances were created by this CLI.
    It uses the tags defined in utils.py to identify 'our' instances.
    """
    count = 0
    # Filter only for running or pending instances (ignore terminated ones)
    instances = ec2.instances.filter(
        Filters=[{'Name': 'instance-state-name', 'Values': ['running', 'pending']}]
    )

    for instance in instances:
        if instance.tags:
            for tag in instance.tags:
                # Check if the instance has our specific Creator tag
                if tag['Key'] == TAG_KEY and tag['Value'] == TAG_VALUE:
                    count += 1
    return count


def create_instance(instance_type, os_type, name):
    """
    Main logic to create an EC2 instance.
    Enforces policies: Max 2 instances, specific types only.
    """

    # 1. Policy Check: Instance Type
    if instance_type not in ['t3.micro', 't2.small']:
        click.echo(click.style("Error: Policy violation. Only t3.micro or t2.small are allowed.", fg="red"))
        return

    # 2. Policy Check: Quantity Limit (Hard Cap)
    current_count = count_our_instances()
    if current_count >= 2:
        click.echo(click.style(
            f"Error: Limit reached! You already have {current_count} running instances created by this tool.",
            fg="red"))
        return

    click.echo(f"Finding latest AMI for {os_type}...")
    try:
        ami_id = get_latest_ami(os_type)
        click.echo(f"Selected AMI: {ami_id}")
    except Exception as e:
        click.echo(click.style(f"Error finding AMI: {e}", fg="red"))
        return

    # --- Tagging Logic ---
    # We need to prepare the tags list BEFORE creating the instance.
    # First, get the mandatory tags (CreatedBy, Owner)
    tags = get_common_tags()

    # Then, append the 'Name' tag provided by the user
    # This ensures the instance has a visible name in the AWS Console
    tags.append({'Key': 'Name', 'Value': name})

    # 3. Launch the Instance
    click.echo(f"Launching instance '{name}'...")
    try:
        instances = ec2.create_instances(
            ImageId=ami_id,
            MinCount=1,
            MaxCount=1,
            InstanceType=instance_type,
            # Apply the combined list of tags to the new instance
            TagSpecifications=[
                {
                    'ResourceType': 'instance',
                    'Tags': tags
                }
            ]
        )

        new_instance_id = instances[0].id
        click.echo(click.style(f"Success! Instance '{name}' ({new_instance_id}) created successfully.", fg="green"))

    except Exception as e:
        click.echo(click.style(f"AWS Error: {e}", fg="red"))

