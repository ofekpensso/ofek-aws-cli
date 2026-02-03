import boto3
import getpass
import random
import string
from botocore.exceptions import NoCredentialsError, PartialCredentialsError, ClientError
import click

TAG_KEY = "CreatedBy"
TAG_VALUE = "OFEK-AWS-CLI"

def get_common_tags():
    """
    Returns a list of tags that must be applied to every resource.
    Includes a dynamic 'Owner' tag based on the current system username.
    """
    user_name = getpass.getuser()
    return [
        {'Key': TAG_KEY, 'Value': TAG_VALUE},
        {'Key': 'owner', 'Value': user_name}
    ]

def get_boto3_resource(service_name):
    """
    Connects to AWS and returns a boto3 'Resource' object.
    """
    try:
        session = boto3.Session()
        return session.resource(service_name)
    except (NoCredentialsError, PartialCredentialsError):
        click.echo(click.style("Error: AWS credentials not found. Please run 'aws configure'.", fg="red"))
        exit(1)
    except ClientError as e:
        click.echo(click.style(f"AWS Error: {e}", fg="red"))
        exit(1)


def get_boto3_client(service_name):
    """
    Connects to AWS and returns a boto3 'Client' object.
    """
    try:
        session = boto3.Session()
        return session.client(service_name)
    except (NoCredentialsError, PartialCredentialsError):
        click.echo(click.style("Error: AWS credentials not found. Please run 'aws configure'.", fg="red"))
        exit(1)
    except ClientError as e:
        click.echo(click.style(f"AWS Error: {e}", fg="red"))
        exit(1)

def generate_bucket_name(prefix):
    """
    Generates a globally unique bucket name.
    S3 bucket names must be unique across ALL AWS accounts.
    Format: <prefix>-<6_random_chars>
    """
    # Generate 6 random lowercase letters/numbers
    random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"{prefix}-{random_suffix}"