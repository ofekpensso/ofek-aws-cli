import click
import boto3
import os
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

    s3_client.put_bucket_versioning(
        Bucket=bucket_name,
        VersioningConfiguration={'Status': 'Enabled'}
    )
    click.echo(click.style(f"Versioning enabled (Data Protection).", fg="green"))


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


def upload_file(bucket_name, file_path):
    """
    Uploads a file to an S3 bucket.
    Enforces a STRICT policy: Can only upload to buckets created by this CLI.
    """

    # 1. Local File Validation
    if not os.path.exists(file_path):
        click.echo(click.style(f"Error: The file '{file_path}' does not exist.", fg="red"))
        return

    file_name = os.path.basename(file_path)
    click.echo(f"Preparing to upload '{file_name}' to bucket '{bucket_name}'...")

    # 2. Bucket Validation (Check Tags)
    try:
        # Fetch tags from the bucket
        tag_set = s3_client.get_bucket_tagging(Bucket=bucket_name).get('TagSet', [])

        # Verify ownership
        is_ours = False
        for tag in tag_set:
            if tag['Key'] == TAG_KEY and tag['Value'] == TAG_VALUE:
                is_ours = True
                break

        if not is_ours:
            click.echo(
                click.style(f"Error: Access Denied! Bucket '{bucket_name}' was not created by this CLI.", fg="red"))
            return

        # 3. Perform Upload
        # We use upload_file which handles large files automatically
        s3_client.upload_file(file_path, bucket_name, file_name)

        click.echo(click.style(f"Success! File '{file_name}' uploaded to '{bucket_name}'.", fg="green"))

    except ClientError as e:
        # Handle cases where bucket doesn't exist or has no tags at all
        if "NoSuchTagSet" in str(e):
            click.echo(click.style(f"Error: Access Denied! Bucket '{bucket_name}' has no tags (not created by CLI).",
                                   fg="red"))
        elif "NoSuchBucket" in str(e):
            click.echo(click.style(f"Error: Bucket '{bucket_name}' does not exist.", fg="red"))
        else:
            click.echo(click.style(f"AWS Error: {e}", fg="red"))


def delete_bucket(bucket_name, force):
    """
    Deletes an S3 bucket.
    - Verifies ownership (CreatedBy tag).
    - Handles non-empty buckets via --force flag.
    """
    click.echo(f"Attempting to delete bucket '{bucket_name}'...")

    try:
        # 1. Ownership Check
        try:
            tag_set = s3_client.get_bucket_tagging(Bucket=bucket_name).get('TagSet', [])
        except ClientError as e:
            if "NoSuchBucket" in str(e):
                click.echo(click.style(f"Error: Bucket '{bucket_name}' does not exist.", fg="red"))
                return
            if "NoSuchTagSet" in str(e):
                click.echo(click.style(f"Error: Access Denied! Bucket '{bucket_name}' has no tags.", fg="red"))
                return
            raise e

        is_ours = False
        for tag in tag_set:
            if tag['Key'] == TAG_KEY and tag['Value'] == TAG_VALUE:
                is_ours = True
                break

        if not is_ours:
            click.echo(
                click.style(f"Error: Access Denied! Bucket '{bucket_name}' was not created by this CLI.", fg="red"))
            return

        # 2. Empty the bucket (if needed)
        bucket = s3_resource.Bucket(bucket_name)

        # Check if empty (we peek at versions now, not just objects)
        # Note: We check object_versions to catch hidden files too
        version_count = sum(1 for _ in bucket.object_versions.limit(1))

        if version_count > 0:
            if not force:
                click.echo(click.style(f"Error: Bucket is not empty! Use --force to delete it and all its contents.",
                                       fg="yellow"))
                return
            else:
                click.echo(click.style("Force delete enabled: Deleting ALL versions and markers...", fg="yellow"))

                bucket.object_versions.all().delete()

        # 3. Delete the Bucket
        bucket.delete()
        click.echo(click.style(f"Success! Bucket '{bucket_name}' deleted.", fg="red"))

    except ClientError as e:
        click.echo(click.style(f"AWS Error: {e}", fg="red"))