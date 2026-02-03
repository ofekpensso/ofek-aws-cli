import click
import boto3
from botocore.exceptions import ClientError
from rich.console import Console
from rich.table import Table
from utils import get_boto3_client, get_common_tags, TAG_KEY, TAG_VALUE

# We need Route53 to manage DNS, and EC2 to validate IPs
r53_client = get_boto3_client('route53')
ec2_client = get_boto3_client('ec2')


# --- Helper Functions ---

def validate_zone_ownership(zone_id):
    """
    Validates that the Hosted Zone was created by this CLI.
    """
    try:
        tags_response = r53_client.list_tags_for_resource(
            ResourceType='hostedzone',
            ResourceId=zone_id
        )
        for tag in tags_response['ResourceTagSet']['Tags']:
            if tag['Key'] == TAG_KEY and tag['Value'] == TAG_VALUE:
                return True
        return False
    except ClientError:
        return False


def validate_ip_ownership(ip_address):
    """
    Checks if the given IP belongs to an EC2 instance created by OUR tool.
    """
    try:
        response = ec2_client.describe_instances(
            Filters=[
                {'Name': 'ip-address', 'Values': [ip_address]},
                {'Name': 'tag:' + TAG_KEY, 'Values': [TAG_VALUE]},
                {'Name': 'instance-state-name', 'Values': ['running']}
            ]
        )
        for reservation in response['Reservations']:
            if reservation['Instances']:
                return True
        return False
    except ClientError:
        return False


# --- Core Functions ---

def create_hosted_zone(domain_name):
    """Creates a Public Hosted Zone and tags it."""
    click.echo(f"Creating Hosted Zone for '{domain_name}'...")
    import time
    caller_ref = f"{domain_name}-{int(time.time())}"

    try:
        response = r53_client.create_hosted_zone(
            Name=domain_name,
            CallerReference=caller_ref,
            HostedZoneConfig={'Comment': 'Created by Platform-CLI', 'PrivateZone': False}
        )
        zone_id = response['HostedZone']['Id'].split('/')[-1]

        # Tag the resource
        r53_client.change_tags_for_resource(
            ResourceType='hostedzone',
            ResourceId=zone_id,
            AddTags=get_common_tags()
        )

        click.echo(click.style(f"Success! Hosted Zone created.", fg="green"))
        click.echo(f"Zone ID: {zone_id}")
        click.echo(f"Name Servers: {', '.join(response['DelegationSet']['NameServers'])}")

    except ClientError as e:
        click.echo(click.style(f"AWS Error: {e}", fg="red"))


def delete_hosted_zone(zone_id):
    """Deletes a Hosted Zone (Only if created by CLI)."""

    # 1. Ownership Check
    if not validate_zone_ownership(zone_id):
        click.echo(click.style(f"Error: Access Denied! Zone '{zone_id}' was not created by this CLI.", fg="red"))
        return

    click.echo(f"Attempting to delete zone '{zone_id}'...")
    try:
        r53_client.delete_hosted_zone(Id=zone_id)
        click.echo(click.style(f"Success! Zone '{zone_id}' deleted.", fg="green"))
    except ClientError as e:
        if "HostedZoneNotEmpty" in str(e):
            click.echo(click.style(f"Error: Zone is not empty! You must delete all records (except NS/SOA) first.",
                                   fg="yellow"))
        else:
            click.echo(click.style(f"AWS Error: {e}", fg="red"))


def create_record(zone_id, record_name, ip_address):
    """Creates/Updates an A-Record. Verifies both Zone and IP ownership."""

    # 1. Zone Ownership Check (The missing requirement!)
    if not validate_zone_ownership(zone_id):
        click.echo(click.style(f"Error: Access Denied! Zone '{zone_id}' was not created by this CLI.", fg="red"))
        return

    # 2. IP Ownership Check
    if not validate_ip_ownership(ip_address):
        click.echo(click.style(f"Error: Access Denied! IP {ip_address} is not from a managed instance.", fg="red"))
        return

    try:
        r53_client.change_resource_record_sets(
            HostedZoneId=zone_id,
            ChangeBatch={
                'Comment': 'Created by Platform-CLI',
                'Changes': [{
                    'Action': 'UPSERT',
                    'ResourceRecordSet': {
                        'Name': record_name,
                        'Type': 'A',
                        'TTL': 300,
                        'ResourceRecords': [{'Value': ip_address}]
                    }
                }]
            }
        )
        click.echo(click.style(f"Success! Record '{record_name}' -> {ip_address} set.", fg="green"))
    except ClientError as e:
        click.echo(click.style(f"AWS Error: {e}", fg="red"))


def delete_record(zone_id, record_name, ip_address):
    """Deletes an A-Record."""

    # 1. Zone Ownership Check
    if not validate_zone_ownership(zone_id):
        click.echo(click.style(f"Error: Access Denied! Zone '{zone_id}' was not created by this CLI.", fg="red"))
        return

    click.echo(f"Deleting record '{record_name}' pointing to {ip_address}...")
    try:
        r53_client.change_resource_record_sets(
            HostedZoneId=zone_id,
            ChangeBatch={
                'Changes': [{
                    'Action': 'DELETE',
                    'ResourceRecordSet': {
                        'Name': record_name,
                        'Type': 'A',
                        'TTL': 300,
                        'ResourceRecords': [{'Value': ip_address}]
                    }
                }]
            }
        )
        click.echo(click.style(f"Success! Record deleted.", fg="green"))
    except ClientError as e:
        click.echo(click.style(f"AWS Error: {e}", fg="red"))


def list_zones():
    """Lists only CLI-created zones."""
    console = Console()
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Zone ID", style="dim")
    table.add_column("Domain Name", style="white")

    try:
        zones = r53_client.list_hosted_zones()['HostedZones']
        found_any = False
        for zone in zones:
            zone_id = zone['Id'].split('/')[-1]
            if validate_zone_ownership(zone_id):
                found_any = True
                table.add_row(zone_id, zone['Name'])

        if found_any:
            console.print(table)
        else:
            click.echo("No zones found.")
    except ClientError as e:
        click.echo(click.style(f"AWS Error: {e}", fg="red"))


def list_records(zone_id):
    """Lists records in a zone."""
    # We verify ownership here too for good measure, though list is usually less strict
    if not validate_zone_ownership(zone_id):
        click.echo(click.style(f"Error: Access Denied! Zone '{zone_id}' not created by CLI.", fg="red"))
        return

    console = Console()
    table = Table(show_header=True, header_style="bold blue")
    table.add_column("Name", style="white")
    table.add_column("Type", style="cyan")
    table.add_column("Value", style="green")

    try:
        response = r53_client.list_resource_record_sets(HostedZoneId=zone_id)
        for r in response['ResourceRecordSets']:
            vals = ", ".join([x['Value'] for x in r.get('ResourceRecords', [])])
            table.add_row(r['Name'], r['Type'], vals)
        console.print(table)
    except ClientError as e:
        click.echo(click.style(f"AWS Error: {e}", fg="red"))