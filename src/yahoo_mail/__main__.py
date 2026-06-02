from yahoo_mail.cli import app
import yahoo_mail.cli.folders  # noqa: F401  registers: login, folders, count, stats
import yahoo_mail.cli.delete   # noqa: F401  registers: purge, clean, batch-nuke, batch-clean, delete-from, rm-folder
import yahoo_mail.cli.sender   # noqa: F401  registers: nuke-sender, batch-nuke-sender
import yahoo_mail.cli.move     # noqa: F401  registers: move
import yahoo_mail.cli.status   # noqa: F401  registers: request-status

if __name__ == "__main__":
    app()
