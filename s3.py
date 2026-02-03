import click
import boto3
from botocore.exceptions import ClientError
from rich.console import Console
from rich.table import Table
from utils import get_boto3_resource, get_boto3_client, get_common_tags, generate_bucket_name, TAG_KEY, TAG_VALUE

# Initialize S3 connections
s3_resource = get_boto3_resource('s3')
s3_client = get_boto3_client('s3')


def create_bucket(bucket_prefix, is_public):
    """
    Creates a new S3 bucket with a unique name.
    Handles 'Public' vs 'Private' security settings and enforces Encryption.
    """

    # 1. Generate unique name
    bucket_name = generate_bucket_name(bucket_prefix)

    # 2. Safety Guardrail: Confirm Public Access
    if is_public:
        click.echo(
            click.style(f"WARNING: You are about to create a PUBLIC bucket '{bucket_name}'.", fg="yellow", bold=True))
        click.echo("This means anyone on the internet might be able to access files in this bucket.")
        if not click.confirm("Are you sure you want to proceed?"):
            click.echo("Operation cancelled.")
            return

    click.echo(f"Creating bucket '{bucket_name}'...")

    try:
        # 3. Create the Bucket
        s3_resource.create_bucket(Bucket=bucket_name)

        # 4. Apply Tags
        s3_client.put_bucket_tagging(
            Bucket=bucket_name,
            Tagging={'TagSet': get_common_tags()}
        )

        # We explicitly set Server-Side Encryption with S3-managed keys (AES256)
        s3_client.put_bucket_encryption(
            Bucket=bucket_name,
            ServerSideEncryptionConfiguration={
                'Rules': [
                    {
                        'ApplyServerSideEncryptionByDefault': {
                            'SSEAlgorithm': 'AES256'
                        }
                    },
                ]
            }
        )
        click.echo(click.style(f"Encryption enabled (AES256).", fg="green"))

        # 6. Handle Public/Private Configuration
        if is_public:
            s3_client.put_public_access_block(
                Bucket=bucket_name,
                PublicAccessBlockConfiguration={
                    'BlockPublicAcls': False,
                    'IgnorePublicAcls': False,
                    'BlockPublicPolicy': False,
                    'RestrictPublicBuckets': False
                }
            )
            click.echo(click.style(f"Bucket set to PUBLIC (Block Access Disabled).", fg="red"))
        else:
            s3_client.put_public_access_block(
                Bucket=bucket_name,
                PublicAccessBlockConfiguration={
                    'BlockPublicAcls': True,
                    'IgnorePublicAcls': True,
                    'BlockPublicPolicy': True,
                    'RestrictPublicBuckets': True
                }
            )
            click.echo(click.style(f"Bucket set to PRIVATE (Secure).", fg="green"))

        click.echo(click.style(f"Success! Bucket '{bucket_name}' created.", fg="green"))

    except ClientError as e:
        click.echo(click.style(f"AWS Error: {e}", fg="red"))


def list_buckets():
    """
    Lists all buckets created by this tool.
    """
    console = Console()
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Bucket Name", style="white")
    table.add_column("Creation Date", style="dim")

    click.echo("Fetching buckets (this might take a moment to scan tags)...")

    found_any = False

    try:
        for bucket in s3_resource.buckets.all():
            try:
                tag_set = s3_client.get_bucket_tagging(Bucket=bucket.name).get('TagSet', [])

                is_ours = False
                for tag in tag_set:
                    if tag['Key'] == TAG_KEY and tag['Value'] == TAG_VALUE:
                        is_ours = True
                        break

                if is_ours:
                    found_any = True
                    table.add_row(
                        bucket.name,
                        str(bucket.creation_date.strftime("%Y-%m-%d %H:%M:%S"))
                    )

            except ClientError as e:
                continue

        if found_any:
            console.print(table)
        else:
            click.echo(click.style("No buckets found created by platform-cli.", fg="yellow"))

    except ClientError as e:
        click.echo(click.style(f"AWS Error: {e}", fg="red"))