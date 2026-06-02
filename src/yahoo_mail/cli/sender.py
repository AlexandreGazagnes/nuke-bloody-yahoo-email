from __future__ import annotations

import typer

from yahoo_mail.cli import _get_client, app, console


@app.command(name="nuke-sender")
def nuke_sender(
    sender: str  = typer.Argument(..., help="Sender address to purge (e.g. notifications@github.com)"),
    yes:    bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
) -> None:
    """Permanently delete ALL emails from a specific sender across every folder."""
    client = _get_client()
    try:
        console.print(f"Scanning all folders for mail from [cyan]{sender}[/cyan] …\n")
        hits = client.count_from_sender(sender)

        if not hits:
            console.print(f"[green]No emails found from[/green] [cyan]{sender}[/cyan].")
            return

        total = sum(n for _, n in hits)
        console.print(f"[bold]Found {total} email(s) from[/bold] [cyan]{sender}[/cyan]:\n")
        for folder_name, n in hits:
            console.print(f"  [cyan]{folder_name}[/cyan]: {n} message(s)")

        if not yes:
            typer.confirm(f"\nPermanently delete all {total} message(s)?", abort=True)

        deleted_total = 0

        def on_folder(folder_name: str, n: int) -> None:
            nonlocal deleted_total
            deleted_total += n
            console.print(f"  [green]✓[/green] [cyan]{folder_name}[/cyan]: deleted {n}")

        console.print()
        client.purge_from_sender(sender, on_folder=on_folder)
    finally:
        client.logout()

    console.print(
        f"\n[green]✓ Done.[/green] [bold]{deleted_total}[/bold] message(s) from "
        f"[cyan]{sender}[/cyan] permanently deleted."
    )


@app.command(name="batch-nuke-sender")
def batch_nuke_sender(
    sender: str   = typer.Argument(..., help="Sender address to purge (e.g. newsletters@shop.com)"),
    yes:    bool  = typer.Option(False, "--yes",  "-y", help="Skip confirmation prompt"),
    batch:  int   = typer.Option(1000,  "--batch", "-b", help="UIDs per round (default 1000)"),
    wait:   float = typer.Option(12.0,  "--wait",  "-w", help="Seconds between rounds (default 12)"),
) -> None:
    """Batch-delete all emails from a sender across every folder, round by round."""
    client = _get_client()
    try:
        console.print(f"Scanning all folders for mail from [cyan]{sender}[/cyan] …\n")
        hits = client.count_from_sender(sender)

        if not hits:
            console.print(f"[green]No emails found from[/green] [cyan]{sender}[/cyan].")
            return

        total = sum(n for _, n in hits)
        console.print(f"[bold]Found {total} email(s) from[/bold] [cyan]{sender}[/cyan]:\n")
        for folder_name, n in hits:
            console.print(f"  [cyan]{folder_name}[/cyan]: {n} messages (~{-(-n // batch)} round(s))")
        console.print(f"\n  Batch: {batch} UIDs/round │ Wait: {wait}s between rounds\n")

        if not yes:
            typer.confirm(f"Permanently delete all {total} message(s)?", abort=True)

        console.print()
        current_folder: list[str] = []

        def on_round(folder_name: str, round_num: int, deleted: int, total_del: int, remaining: int) -> None:
            if not current_folder or current_folder[0] != folder_name:
                current_folder.clear()
                current_folder.append(folder_name)
                console.print(f"\n[bold]── {folder_name} ──[/bold]")
            remaining_str = str(remaining) if remaining else "[green]0 — folder clean[/green]"
            console.print(
                f"  Round [bold]{round_num:>4}[/bold] │ "
                f"deleted [yellow]{deleted:>5}[/yellow] │ "
                f"total [magenta]{total_del:>8}[/magenta] │ "
                f"remaining {remaining_str}"
                + (f" │ waiting {wait}s …" if remaining else "")
            )

        grand_total = client.batch_nuke_sender(sender, batch=batch, wait=wait, on_round=on_round)
    finally:
        client.logout()

    console.print(
        f"\n[green]✓ Done.[/green] [bold]{grand_total}[/bold] message(s) from "
        f"[cyan]{sender}[/cyan] permanently deleted."
    )
