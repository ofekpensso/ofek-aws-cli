import click
import os
from botocore.exceptions import ClientError
from rich.console import Console
from rich.table import Table
from utils import get_boto3_resource, get_boto3_client, get_common_tags, generate_bucket_name, TAG_KEY, TAG_VALUE
import json
# Initialize S3 connections
s3_resource = get_boto3_resource('s3')
s3_client = get_boto3_client('s3')


def create_bucket(bucket_prefix, is_public=False):
    """
    Creates a new S3 bucket.
    Handles 'Public' via Bucket Policy (The modern way) vs 'Private'.
    """
    # 1. Generate Name
    bucket_name = generate_bucket_name(bucket_prefix)

    # 2. Guardrail
    if is_public:
        click.echo(
            click.style(f"WARNING: You are about to create a PUBLIC bucket '{bucket_name}'.", fg="yellow", bold=True))
        if not click.confirm("Are you sure you want to proceed?"):
            click.echo("Operation cancelled.")
            return

    click.echo(f"Creating bucket '{bucket_name}'...")

    try:
        # 3. Create
        s3_client.create_bucket(Bucket=bucket_name)
        s3_client.get_waiter('bucket_exists').wait(Bucket=bucket_name)

        # 4. Tags
        s3_client.put_bucket_tagging(
            Bucket=bucket_name,
            Tagging={'TagSet': get_common_tags()}
        )

        # 5. Encryption
        s3_client.put_bucket_encryption(
            Bucket=bucket_name,
            ServerSideEncryptionConfiguration={
                'Rules': [{'ApplyServerSideEncryptionByDefault': {'SSEAlgorithm': 'AES256'}}]
            }
        )
        click.echo(click.style(f"Encryption enabled (AES256).", fg="green"))

        # --- 6. PUBLIC / PRIVATE LOGIC (UPDATED) ---
        if is_public:
            # PUBLIC MODE
            s3_client.delete_public_access_block(Bucket=bucket_name)

            bucket_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "PublicReadGetObject",
                        "Effect": "Allow",
                        "Principal": "*",
                        "Action": "s3:GetObject",
                        "Resource": f"arn:aws:s3:::{bucket_name}/*"
                    }
                ]
            }

            s3_client.put_bucket_policy(Bucket=bucket_name, Policy=json.dumps(bucket_policy))
            click.echo(click.style("⚠️  Bucket set to PUBLIC via Bucket Policy!", fg="red", bold=True))

        else:
            # PRIVATE MODE
            s3_client.put_public_access_block(
                Bucket=bucket_name,
                PublicAccessBlockConfiguration={
                    'BlockPublicAcls': True,
                    'IgnorePublicAcls': True,
                    'BlockPublicPolicy': True,
                    'RestrictPublicBuckets': True
                }
            )
            click.echo(click.style("Bucket set to PRIVATE (Secure).", fg="green"))

        # 7. Versioning
        s3_client.put_bucket_versioning(
            Bucket=bucket_name,
            VersioningConfiguration={'Status': 'Enabled'}
        )
        click.echo(click.style(f"Success! Bucket '{bucket_name}' created.", fg="green", bold=True))

    except ClientError as e:
        error_code = e.response['Error']['Code']
        if 'InvalidBucketName' in str(e) or 'InvalidBucketName' == error_code:
            click.echo(click.style(f"Error: Invalid bucket name '{bucket_prefix}'.", fg="red"))
        elif 'BucketAlreadyExists' == error_code:
            click.echo(click.style(f"Error: Bucket '{bucket_name}' already exists.", fg="red"))
        else:
            click.echo(click.style(f"AWS Error: {e}", fg="red"))
        return

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


def get_managed_buckets():
    """
    Returns a list of S3 bucket names created by this CLI.
    """
    found_buckets = []
    try:
        # Use Client to list all buckets (Resource generic iteration can be slower/less detailed)
        response = s3_client.list_buckets()

        for bucket in response['Buckets']:
            name = bucket['Name']
            try:
                # Use Client to fetch tags for each bucket
                tags = s3_client.get_bucket_tagging(Bucket=name).get('TagSet', [])
                for tag in tags:
                    if tag['Key'] == TAG_KEY and tag['Value'] == TAG_VALUE:
                        found_buckets.append(name)
                        break
            except ClientError:
                # Continue if bucket has no tags or access is denied
                continue
    except ClientError:
        pass

    return found_buckets


def delete_all_buckets():
    """
    Finds and deletes ALL S3 buckets created by this CLI.
    Forces deletion of objects and versions.
    """
    click.echo("Scanning for S3 buckets to delete (this might take a moment)...")

    # Step 1: Find our buckets using the helper function
    buckets_to_delete = get_managed_buckets()

    if not buckets_to_delete:
        click.echo(click.style("No S3 buckets found.", fg="yellow"))
        return

    # Step 2: Delete them using s3_resource
    for bucket_name in buckets_to_delete:
        try:
            click.echo(f"Deleting bucket {bucket_name}...")

            # Using s3_resource here because it handles object/version deletion easily
            bucket = s3_resource.Bucket(bucket_name)

            # Delete all versions (if versioning was enabled)
            bucket.object_versions.delete()
            # Delete all remaining objects
            bucket.objects.all().delete()
            # Delete the bucket itself
            bucket.delete()

            click.echo(click.style(f"Deleted {bucket_name}", fg="green"))

        except ClientError as e:
            click.echo(click.style(f"Failed to delete {bucket_name}: {e}", fg="red"))