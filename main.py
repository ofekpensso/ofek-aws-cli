import click
import ec2 as ec2_ops  # We import our EC2 logic module and give it a nickname 'ec2_ops'
import s3 as s3_ops
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
def delete(identifier):
    """Terminate an EC2 instance (Irreversible!)."""

    # Safety Prompt: Force the user to confirm the action
    if click.confirm(f"WARNING: Are you sure you want to PERMANENTLY delete {identifier}?"):
        ec2_ops.terminate_instance(identifier)
    else:
        click.echo("Operation cancelled.")

# --- S3 Group (Placeholders for later) ---
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

# --- Route53 Group (Placeholders for later) ---
@cli.group()
def route53():
    """Manage Route53 DNS Zones."""
    pass

if __name__ == '__main__':
    cli()