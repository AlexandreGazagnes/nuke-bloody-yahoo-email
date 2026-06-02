from __future__ import annotations

IMAP_HOST  = "imap.mail.yahoo.com"
IMAP_PORT  = 993
BATCH_SIZE = 1000   # Yahoo IMAP CAPABILITY advertises MESSAGELIMIT=1000
DELAY      = 0.5    # seconds between batches — Yahoo rate-limits on bulk ops

ALIASES: dict[str, list[str]] = {
    "spam":    ["Bulk Mail", "Spam", "Junk", "Junk E-mail"],
    "trash":   ["Trash", "Deleted", "Deleted Messages"],
    "archive": ["Archive", "Archived", "Archives"],
    "sent":    ["Sent", "Sent Items", "Sent Messages"],
    "drafts":  ["Draft", "Drafts"],
    "inbox":   ["INBOX", "Inbox"],
}
