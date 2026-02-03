import click
import boto3
from botocore.exceptions import ClientError
from rich.console import Console
from rich.table import Table
from utils import get_boto3_client, get_common_tags, TAG_KEY, TAG_VALUE

# We need Route53 to manage DNS, and EC2 to validate IPs
r53_client = get_boto3_client('route53')
ec2_client = get_boto3_client('ec2')


def create_hosted_zone(domain_name):
    """
    Creates a Public Hosted Zone.
    Tags it automatically so we can manage it later.
    """
    click.echo(f"Creating Hosted Zone for '{domain_name}'...")

    # Route53 requires a unique string (CallerReference) to prevent duplicates
    import time
    caller_ref = f"{domain_name}-{int(time.time())}"

    try:
        response = r53_client.create_hosted_zone(
            Name=domain_name,
            CallerReference=caller_ref,
            HostedZoneConfig={'Comment': 'Created by Platform-CLI', 'PrivateZone': False}
        )

        zone_id = response['HostedZone']['Id']
        # Zone ID usually comes like '/hostedzone/Z0123456...', we strip the prefix if needed
        clean_zone_id = zone_id.split('/')[-1]

        # Tag the resource (Route53 uses a different API for tagging than EC2/S3)
        r53_client.change_tags_for_resource(
            ResourceType='hostedzone',
            ResourceId=clean_zone_id,
            AddTags=get_common_tags()
        )

        click.echo(click.style(f"Success! Hosted Zone created.", fg="green"))
        click.echo(f"Zone ID: {clean_zone_id}")
        click.echo(f"Name Servers: {', '.join(response['DelegationSet']['NameServers'])}")

    except ClientError as e:
        click.echo(click.style(f"AWS Error: {e}", fg="red"))


def validate_ip_ownership(ip_address):
    """
    Helper function: Checks if the given IP belongs to an EC2 instance
    created by OUR tool (has the specific tags).
    """
    try:
        # Search for instances with this Public IP AND our Tag
        response = ec2_client.describe_instances(
            Filters=[
                {'Name': 'ip-address', 'Values': [ip_address]},
                {'Name': 'tag:' + TAG_KEY, 'Values': [TAG_VALUE]},
                {'Name': 'instance-state-name', 'Values': ['running']}
            ]
        )

        # If we found any reservation -> instance -> it's valid
        for reservation in response['Reservations']:
            if reservation['Instances']:
                return True

        return False

    except ClientError:
        return False


def create_record(zone_id, record_name, ip_address):
    """
    Creates an 'A' record (Address) pointing a name to an IP.
    STRICT VALIDATION: The IP must belong to one of our EC2 instances.
    """

    # 1. Validate Ownership (The Cross-Module Check)
    click.echo(f"Validating ownership of IP {ip_address}...")
    if not validate_ip_ownership(ip_address):
        click.echo(click.style(
            f"Error: Access Denied! The IP {ip_address} does not belong to a running instance created by this tool.",
            fg="red"))
        return

    click.echo(f"IP verified. Creating record '{record_name}' -> {ip_address}...")

    try:
        # 2. Create the DNS Record
        r53_client.change_resource_record_sets(
            HostedZoneId=zone_id,
            ChangeBatch={
                'Comment': 'Created by Platform-CLI',
                'Changes': [
                    {
                        'Action': 'UPSERT',  # Create or Update
                        'ResourceRecordSet': {
                            'Name': record_name,
                            'Type': 'A',
                            'TTL': 300,
                            'ResourceRecords': [{'Value': ip_address}]
                        }
                    }
                ]
            }
        )
        click.echo(click.style(f"Success! Record '{record_name}' created/updated.", fg="green"))

    except ClientError as e:
        click.echo(click.style(f"AWS Error: {e}", fg="red"))


def list_zones():
    """
    Lists all Hosted Zones created by this tool.
    Note: Route53 doesn't support server-side filtering by tags in list_hosted_zones.
    We have to fetch all, and verify tags one by one (can be slow, but accurate).
    """
    console = Console()
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Zone ID", style="dim")
    table.add_column("Domain Name", style="white")
    table.add_column("Private Zone", style="cyan")

    click.echo("Fetching zones (scanning tags)...")

    try:
        # Get all zones
        zones = r53_client.list_hosted_zones()['HostedZones']
        found_any = False

        for zone in zones:
            zone_id = zone['Id'].split('/')[-1]
            try:
                # Get tags for this specific zone
                tags_response = r53_client.list_tags_for_resource(
                    ResourceType='hostedzone',
                    ResourceId=zone_id
                )

                # Check for our signature tag
                is_ours = False
                for tag in tags_response['ResourceTagSet']['Tags']:
                    if tag['Key'] == TAG_KEY and tag['Value'] == TAG_VALUE:
                        is_ours = True
                        break

                if is_ours:
                    found_any = True
                    table.add_row(
                        zone_id,
                        zone['Name'],
                        str(zone['Config']['PrivateZone'])
                    )
            except ClientError:
                continue

        if found_any:
            console.print(table)
        else:
            click.echo(click.style("No hosted zones found created by platform-cli.", fg="yellow"))

    except ClientError as e:
        click.echo(click.style(f"AWS Error: {e}", fg="red"))


def list_records(zone_id):
    """
    Lists all DNS records in a specific zone.
    """
    console = Console()
    table = Table(show_header=True, header_style="bold blue")
    table.add_column("Record Name", style="white")
    table.add_column("Type", style="cyan")
    table.add_column("Value (IP)", style="green")
    table.add_column("TTL", style="dim")

    try:
        response = r53_client.list_resource_record_sets(HostedZoneId=zone_id)

        for record in response['ResourceRecordSets']:
            # Extract values (sometimes there are multiple IPs)
            values = [r['Value'] for r in record.get('ResourceRecords', [])]
            value_str = ", ".join(values) if values else "Alias/Other"

            table.add_row(
                record['Name'],
                record['Type'],
                value_str,
                str(record.get('TTL', 'N/A'))
            )

        console.print(table)

    except ClientError as e:
        click.echo(click.style(f"AWS Error: {e}", fg="red"))