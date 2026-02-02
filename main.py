import click
import ec2 as ec2_ops  # We import our EC2 logic module and give it a nickname 'ec2_ops'

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
@click.argument('instance_id')
def stop(instance_id):
    """Stop an EC2 instance (Only if created by CLI)."""
    ec2_ops.stop_instance(instance_id)

@ec2.command()
@click.argument('instance_id')
def start(instance_id):
    """Start an EC2 instance (Only if created by CLI)."""
    ec2_ops.start_instance(instance_id)

# --- S3 Group (Placeholders for later) ---
@cli.group()
def s3():
    """Manage S3 Buckets."""
    pass

# --- Route53 Group (Placeholders for later) ---
@cli.group()
def route53():
    """Manage Route53 DNS Zones."""
    pass

if __name__ == '__main__':
    cli()