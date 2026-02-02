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
        Filters=[
            {
                'Name': 'instance-state-name',
                'Values': ['running', 'pending', 'stopped', 'stopping']
            }
        ]
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


def list_instances():
    """
    Lists all EC2 instances created by this tool.
    Displays them in a formatted table using the 'rich' library.
    """

    # Filter instances that have our specific 'CreatedBy' tag
    # We want to see ALL states (running, stopped, pending) to manage them
    instances = ec2.instances.filter(
        Filters=[
            {'Name': 'tag:' + TAG_KEY, 'Values': [TAG_VALUE]}
        ]
    )

    # Initialize the Rich Console and Table
    console = Console()
    table = Table(show_header=True, header_style="bold magenta")

    # Define table columns
    table.add_column("Instance ID", style="dim")
    table.add_column("Name", style="cyan")
    table.add_column("Type")
    table.add_column("State")
    table.add_column("Public IP", justify="right")

    click.echo("Fetching instances...")

    found_instances = False
    for instance in instances:
        found_instances = True

        # Extract the 'Name' tag if it exists
        name = "N/A"
        if instance.tags:
            for tag in instance.tags:
                if tag['Key'] == 'Name':
                    name = tag['Value']
                    break

        # Add row to the table
        # We use strict string conversion to avoid errors
        table.add_row(
            instance.id,
            name,
            instance.instance_type,
            instance.state['Name'],
            instance.public_ip_address if instance.public_ip_address else "N/A"
        )

    if found_instances:
        console.print(table)
    else:
        click.echo(click.style("No instances found with the platform-cli tag.", fg="yellow"))


def stop_instance(identifier):
    """
    Stops an EC2 instance by Name or ID.
    Only allows stopping instances created by this CLI.
    """
    try:
        # Step 1: Resolve ID from Name (if needed)
        instance_id = get_id_by_name(identifier)

        click.echo(f"Resolved ID: {instance_id}")
        click.echo(f"Attempting to stop instance {instance_id}...")

        # Get the instance object
        instance = ec2.Instance(instance_id)
        instance.load()

        # Validation: Check if the instance has our specific tag
        is_ours = False
        if instance.tags:
            for tag in instance.tags:
                if tag['Key'] == TAG_KEY and tag['Value'] == TAG_VALUE:
                    is_ours = True
                    break

        if not is_ours:
            click.echo(
                click.style(f"Error: Access Denied! Instance {instance_id} was not created by this CLI.", fg="red"))
            return

        # Perform the action
        instance.stop()
        click.echo(click.style(f"Success! Instance '{identifier}' ({instance_id}) is stopping...", fg="yellow"))

    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg="red"))


def start_instance(identifier):
    """
    Starts an EC2 instance by Name or ID.
    Only allows starting instances created by this CLI.
    """
    try:
        # Step 1: Resolve ID from Name (if needed)
        instance_id = get_id_by_name(identifier)

        click.echo(f"Resolved ID: {instance_id}")
        click.echo(f"Attempting to start instance {instance_id}...")

        instance = ec2.Instance(instance_id)
        instance.load()

        # Validation
        is_ours = False
        if instance.tags:
            for tag in instance.tags:
                if tag['Key'] == TAG_KEY and tag['Value'] == TAG_VALUE:
                    is_ours = True
                    break

        if not is_ours:
            click.echo(
                click.style(f"Error: Access Denied! Instance {instance_id} was not created by this CLI.", fg="red"))
            return

        # Perform the action
        instance.start()
        click.echo(click.style(f"Success! Instance '{identifier}' ({instance_id}) is starting...", fg="green"))

    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg="red"))

def get_id_by_name(name_or_id):
    """
    Helper function to resolve an identifier (Name or ID) to a specific Instance ID.
    If input starts with 'i-', assume it's an ID.
    Otherwise, search for an instance with that 'Name' tag.
    """
    # If it looks like an ID, return it as is
    if name_or_id.startswith("i-"):
        return name_or_id

    # Search for instances with this Name AND our Creator tag
    click.echo(f"Searching for instance named '{name_or_id}'...")

    filters = [
        {'Name': 'tag:Name', 'Values': [name_or_id]},
        {'Name': 'tag:' + TAG_KEY, 'Values': [TAG_VALUE]},
        {'Name': 'instance-state-name', 'Values': ['running', 'stopped', 'pending', 'stopping']}
        # Don't find terminated ones
    ]

    found_instances = list(ec2.instances.filter(Filters=filters))

    if len(found_instances) == 0:
        raise Exception(f"No instance found with name '{name_or_id}' (created by this CLI).")

    if len(found_instances) > 1:
        raise Exception(f"Multiple instances found with name '{name_or_id}'. Please use the Instance ID to be safe.")

    # If exactly one found, return its ID
    return found_instances[0].id


def terminate_instance(identifier):
    """
    Terminates an instance by Name or ID.
    """
    try:
        # Step 1: Resolve the ID (Translate Name -> ID if needed)
        instance_id = get_id_by_name(identifier)

        click.echo(f"Resolved ID: {instance_id}")
        click.echo(f"Attempting to terminate instance {instance_id}...")

        instance = ec2.Instance(instance_id)
        instance.load()

        # Validation: Double check ownership tags (Safety first!)
        is_ours = False
        if instance.tags:
            for tag in instance.tags:
                if tag['Key'] == TAG_KEY and tag['Value'] == TAG_VALUE:
                    is_ours = True
                    break

        if not is_ours:
            click.echo(
                click.style(f"Error: Access Denied! Instance {instance_id} was not created by this CLI.", fg="red"))
            return

        # Execute Termination
        instance.terminate()
        click.echo(click.style(f"Success! Instance '{identifier}' ({instance_id}) is being terminated.", fg="red"))

    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg="red"))