import shutil
import sys
from rich.console import Console
from rich.panel import Panel
from rich.align import Align
from rich.text import Text


def show_banner():
    console = Console()

    if shutil.which("ofek-cli") is None:
        error_text = Text("❌ Installation Failed!", style="bold red")
        error_text.append("\nThe command 'ofek-cli' was not found.\n", style="white")
        error_text.append("Try running: pip install -e .", style="yellow")
        console.print(Panel(Align.center(error_text), border_style="red", title="Error"))
        sys.exit(1)

    logo_text = """
 ██████╗ ███████╗███████╗██╗  ██╗     ██████╗██╗     ██╗
██╔══██╗██╔════╝██╔════╝██║ ██╔╝    ██╔════╝██║     ██║
██║  ██║█████╗  █████╗  █████╔╝     ██║     ██║     ██║
██║  ██║██╔══╝  ██╔══╝  ██╔═██╗     ██║     ██║     ██║
██████╔╝██║     ███████╗██║  ██╗    ╚██████╗███████╗██║
╚═════╝ ╚═╝     ╚══════╝╚═╝  ╚═╝     ╚═════╝╚══════╝╚═╝
    """

    combined_text = Text(logo_text, style="bold bright_cyan")
    combined_text.append("\n")

    combined_text.append("\n>> Made by Ofek Pensso | DevOps Engineer 🚀", style="bold yellow")

    combined_text.append("\n\n")

    combined_text.append("Ready to launch? Run: ", style="dim white")
    combined_text.append(" ofek-cli --help ", style="bold black on bright_green")  # כפתור ירוק בולט
    combined_text.append(" to start.", style="dim white")

    final_panel = Panel(
        Align.center(combined_text),
        title="[bold bright_green]Installation Complete![/]",
        subtitle="[bold bright_blue]AWS Platform Engineering Tool[/]",
        border_style="bright_blue",
        padding=(1, 2)
    )

    console.print(final_panel)


if __name__ == "__main__":
    show_banner()