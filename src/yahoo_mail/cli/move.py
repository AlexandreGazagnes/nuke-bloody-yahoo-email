from __future__ import annotations

import typer

from yahoo_mail.cli import _get_client, _resolve_or_exit, app, console


@app.command()
def move(
    src: str  = typer.Argument(..., help="Source folder (name or alias)"),
    dst: str  = typer.Argument(..., help="Destination folder (name or alias)"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
) -> None:
    """Move ALL emails from one folder to another."""
    client = _get_client()
    try:
        real_src = _resolve_or_exit(client, src)
        real_dst = _resolve_or_exit(client, dst)

        n = client.count(real_src)
        if n == 0:
            console.print(f"[cyan]{real_src}[/cyan] is empty — nothing to move.")
            return

        if not yes:
            typer.confirm(f"Move {n} message(s) from '{real_src}' → '{real_dst}'?", abort=True)

        with console.status(f"Moving {n} messages …"):
            moved = client.move_all(real_src, real_dst)
    finally:
        client.logout()

    console.print(
        f"[green]✓[/green] Moved [bold]{moved}[/bold] message(s): "
        f"[cyan]{real_src}[/cyan] → [cyan]{real_dst}[/cyan]."
    )
