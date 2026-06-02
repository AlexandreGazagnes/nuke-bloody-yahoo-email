from __future__ import annotations

import typer
from rich.console import Console

from yahoo_mail.client import YahooMailClient
from yahoo_mail.constants import ALIASES
from yahoo_mail.credentials import prompt_credentials, read_credentials

app = typer.Typer(
    name="yahoo-mail",
    help="Yahoo Mail CLI — manage your mailbox from the terminal.",
    no_args_is_help=True,
)
console = Console()


def _get_client() -> YahooMailClient:
    email, password = read_credentials()
    if not email or not password:
        email, password = prompt_credentials(console)

    console.print(f"Connecting as [cyan]{email}[/cyan] …", end=" ")
    try:
        client = YahooMailClient(email, password)
        console.print("[green]OK[/green]\n")
        return client
    except Exception as exc:
        console.print("[red]FAILED[/red]")
        console.print(f"[red]{exc}[/red]")
        console.print(
            "\n[yellow]Tip:[/yellow] Make sure you are using an App Password,\n"
            "not your regular Yahoo password."
        )
        raise typer.Exit(1)


def _resolve_or_exit(client: YahooMailClient, name: str) -> str:
    real = client.resolve(name)
    if not real:
        known = list(ALIASES.keys())
        console.print(
            f"[red]Folder not found:[/red] [bold]{name}[/bold]\n"
            f"[dim]Use 'yahoo-mail folders' to list available folders.\n"
            f"Known aliases: {', '.join(known)}[/dim]"
        )
        raise typer.Exit(1)
    return real
