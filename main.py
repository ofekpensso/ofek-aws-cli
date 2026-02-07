import click
import ec2 as ec2_ops
import s3 as s3_ops
import route53 as r53_ops
import cleanup_ops
# --- Main Entry Point ---
@click.group()
def cli():
    """
    Platform Engineering CLI Tool.
    Manage AWS resources (EC2, S3, Route53) with safety constraints.
    """
    pass

# --- EC2 Group ---
@cli.group()
def ec2():
    """Manage EC2 Instances (Create, List, Stop, Start)."""
    pass

@ec2.command()
@click.option('--type', default='t3.micro', help='Instance type (t3.micro / t2.small)')
@click.option('--os', default='amazon-linux', type=click.Choice(['ubuntu', 'amazon-linux']), help='Operating System')
@click.option('--name', required=True, help='Name of the instance')
def create(type, os, name):
    """
    Create a new EC2 instance.
    Enforces a limit of 2 instances and specific types.
    """
    # Here is the connection! We pass the user inputs to our logic file.
    ec2_ops.create_instance(type, os, name)

@ec2.command()
def list():
    """List all instances created by this CLI."""
    ec2_ops.list_instances()

@ec2.command()
@click.argument('identifier')
def stop(identifier):
    """Stop an EC2 instance (Only if created by CLI)."""
    ec2_ops.stop_instance(identifier)

@ec2.command()
@click.argument('identifier')
def start(identifier):
    """Start an EC2 instance (Only if created by CLI)."""
    ec2_ops.start_instance(identifier)

@ec2.command()
@click.argument('identifier')
def terminate(identifier):
    """Terminates (deletes) an EC2 instance by Name or ID."""

    # Safety Prompt
    if click.confirm(f"⚠️  WARNING: Are you sure you want to PERMANENTLY terminate {identifier}?"):
        ec2_ops.terminate_instance(identifier)
    else:
        click.echo("Operation cancelled.")

@ec2.command()
@click.argument('identifier')
def delete(identifier):
    """Terminate an EC2 instance (Irreversible!)."""

    # Safety Prompt: Force the user to confirm the action
    if click.confirm(f"WARNING: Are you sure you want to PERMANENTLY delete {identifier}?"):
        ec2_ops.terminate_instance(identifier)
    else:
        click.echo("Operation cancelled.")

# --- S3 Group ---
@cli.group()
def s3():
    """Manage S3 Buckets."""
    pass

@s3.command()
@click.argument('name_prefix')
@click.option('--public', is_flag=True, help="Set the bucket to be publicly accessible (Requires confirmation).")
def create(name_prefix, public):
    """
    Create a new S3 bucket (Private by default).
    The name will be suffixed with random characters for uniqueness.
    """
    s3_ops.create_bucket(name_prefix, public)

@s3.command()
@click.argument('bucket_name')
@click.argument('file_path')
def upload(bucket_name, file_path):
    """
    Upload a file to a bucket (Only if created by CLI).
    Usage: ofek-cli s3 upload <bucket_name> <path_to_file>
    """
    s3_ops.upload_file(bucket_name, file_path)

@s3.command()
def list():
    """List S3 buckets created by this CLI."""
    s3_ops.list_buckets()

@s3.command()
@click.argument('bucket_name')
@click.option('--force', is_flag=True, help="Delete bucket even if it contains files (Empties it first).")
def delete(bucket_name, force):
    """
    Delete an S3 bucket (Only if created by CLI).
    """
    if click.confirm(f"WARNING: Are you sure you want to delete '{bucket_name}'?"):
        s3_ops.delete_bucket(bucket_name, force)
    else:
        click.echo("Operation cancelled.")

# --- Route53 Group ---
@cli.group()
def route53():
    """Manage Route53 DNS Zones and Records."""
    pass

@route53.command()
@click.argument('domain_name')
def create_zone(domain_name):
    """Create a new Public Hosted Zone."""
    r53_ops.create_hosted_zone(domain_name)

@route53.command()
@click.argument('zone_id')
def delete_zone(zone_id):
    """Delete a Hosted Zone (Must be empty)."""
    if click.confirm(f"Are you sure you want to delete zone {zone_id}?"):
        r53_ops.delete_hosted_zone(zone_id)

@route53.command()
def list_zones():
    """List Hosted Zones created by this tool."""
    r53_ops.list_zones()

@route53.command()
@click.argument('zone_id')
@click.argument('record_name')
@click.argument('ip_address')
def add_record(zone_id, record_name, ip_address):
    """Add an A-Record (Verified IPs only)."""
    r53_ops.create_record(zone_id, record_name, ip_address)

@route53.command()
@click.argument('zone_id')
@click.argument('record_name')
@click.argument('ip_address')
def delete_record(zone_id, record_name, ip_address):
    """Delete an A-Record."""
    if click.confirm(f"Delete record {record_name} -> {ip_address}?"):
        r53_ops.delete_record(zone_id, record_name, ip_address)

@route53.command()
@click.argument('zone_id')
def list_records(zone_id):
    """List all DNS records in a Hosted Zone."""
    r53_ops.list_records(zone_id)

@cli.command()
def status():
    """
    📊  Shows a dashboard of ALL active resources.
    Lists EC2 instances, S3 buckets, and Route53 zones managed by this tool.
    """
    cleanup_ops.show_inventory()

@cli.command()
@click.option('--yes', is_flag=True, help="Skip confirmation prompt")
def cleanup(yes):
    """
    ☢️  DANGER: Deletes ALL resources created by this tool.
    Shows a preview of resources to be deleted before executing.
    """
    cleanup_ops.execute_cleanup(yes)

if __name__ == '__main__':
    cli()