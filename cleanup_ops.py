import click
import ec2 as ec2_ops
import s3 as s3_ops
import route53 as r53_ops

def execute_cleanup(yes):
    """
    The actual logic for finding and deleting resources.
    Moved here to keep main.py clean.
    """
    click.echo(click.style("Scanning for resources to delete...", fg="cyan"))

    # 1. Discovery Phase (Find everything)
    instances = ec2_ops.list_instances(print_table=False)
    buckets = s3_ops.get_managed_buckets()
    zones = r53_ops.get_managed_zones()

    total_count = len(instances) + len(buckets) + len(zones)

    if total_count == 0:
        click.echo(click.style("No resources found. Environment is clean! ✨", fg="green"))
        return

    # 2. Preview Phase (Show the list)
    click.echo(click.style(f"\nFound {total_count} resources managed by platform-cli:", fg="yellow", bold=True))

    if instances:
        click.echo(click.style(f"\n[EC2 Instances] ({len(instances)})", bold=True))
        for i in instances:
            click.echo(f" - {i['id']} ({i['name']})")

    if buckets:
        click.echo(click.style(f"\n[S3 Buckets] ({len(buckets)})", bold=True))
        for b in buckets:
            click.echo(f" - {b}")

    if zones:
        click.echo(click.style(f"\n[Route53 Zones] ({len(zones)})", bold=True))
        for z in zones:
            click.echo(f" - {z['name']} ({z['id']})")

    # 3. Confirmation Phase (The Red Button)
    click.echo("")
    if not yes:
        if not click.confirm(
                click.style("⚠️  Are you sure you want to PERMANENTLY DELETE these resources?", fg="red", bold=True)):
            click.echo("Cleanup aborted.")
            return

    # 4. Execution Phase (Delete everything)
    click.echo(click.style("\n--- Starting Cleanup ---", fg="white", bold=True))

    if instances:
        ec2_ops.terminate_all_instances()

    if buckets:
        s3_ops.delete_all_buckets()

    if zones:
        r53_ops.delete_all_zones()

    click.echo(click.style("\nCleanup complete! 🧹", fg="green", bold=True))