from __future__ import annotations

import getpass
from pathlib import Path

PWD_FILE = Path("PWD.txt")


def read_credentials() -> tuple[str, str]:
    if not PWD_FILE.exists():
        return "", ""
    data: dict[str, str] = {}
    for line in PWD_FILE.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            data[k.strip()] = v.strip()
    return data.get("EMAIL", ""), data.get("PASSWORD", "")


def save_credentials(email: str, password: str) -> None:
    PWD_FILE.write_text(f"EMAIL={email}\nPASSWORD={password}\n", encoding="utf-8")
    PWD_FILE.chmod(0o600)


def prompt_credentials(console=None) -> tuple[str, str]:
    if console:
        console.print("[bold yellow]First-time setup — Yahoo credentials[/bold yellow]")
        console.print(
            "[dim]Yahoo IMAP requires an App Password (not your regular password).\n"
            "Generate one at: myaccount.yahoo.com → Security → App passwords[/dim]\n"
        )
    import typer
    email    = typer.prompt("Yahoo email address")
    password = getpass.getpass("App Password (hidden): ")
    save_credentials(email, password)
    if console:
        console.print(f"[green]Credentials saved to {PWD_FILE.resolve()}[/green]\n")
    return email, password
