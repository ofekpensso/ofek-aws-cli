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


def show_inventory():
    """
    Scans and displays ALL resources currently managed by this CLI.
    """
    click.echo(click.style("\n📊  Project Status Dashboard", fg="cyan", bold=True))
    click.echo(click.style("==========================", fg="cyan"))
    click.echo("Scanning AWS resources...\n")

    # 1. Scan Everything
    instances = ec2_ops.list_instances(print_table=False)
    buckets = s3_ops.get_managed_buckets()
    zones = r53_ops.get_managed_zones()

    total_count = len(instances) + len(buckets) + len(zones)

    # 2. Display EC2
    if instances:
        click.echo(click.style(f"🖥️   EC2 Instances ({len(instances)})", fg="green", bold=True))
        for i in instances:
            state_color = "green" if i['state'] == 'running' else "yellow"
            state_text = click.style(i['state'], fg=state_color)

            # Safe get for IP
            public_ip = i.get('public_ip', 'No Public IP')

            click.echo(f"  • {i['name']} ({i['id']}) - [{state_text}] - {public_ip}")
    else:
        # TIKUN: dim=True instead of fg="dim"
        click.echo(click.style("🖥️   EC2 Instances: None", dim=True))

    click.echo("")  # Spacer

    # 3. Display S3
    if buckets:
        click.echo(click.style(f"📦  S3 Buckets ({len(buckets)})", fg="yellow", bold=True))
        for b in buckets:
            click.echo(f"  • {b}")
    else:
        # TIKUN: dim=True instead of fg="dim"
        click.echo(click.style("📦  S3 Buckets: None", dim=True))

    click.echo("")  # Spacer

    # 4. Display Route53
    if zones:
        click.echo(click.style(f"🌐  Route53 Zones ({len(zones)})", fg="blue", bold=True))
        for z in zones:
            click.echo(f"  • {z['name']} ({z['id']})")
    else:
        # TIKUN: dim=True instead of fg="dim"
        click.echo(click.style("🌐  Route53 Zones: None", dim=True))

    # 5. Summary
    click.echo(click.style("--------------------------", fg="cyan"))
    if total_count > 0:
        click.echo(click.style(f"✅ Total Managed Resources: {total_count}", bold=True))
    else:
        click.echo(click.style("✨ Environment is clean (0 resources).", fg="green"))
    click.echo("")