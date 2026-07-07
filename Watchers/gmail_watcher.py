#!/usr/bin/env python3
"""
Gmail Watcher for AI Employee Vault.

Polls Gmail over IMAP for unread messages and creates a task file in
/Needs_Action for each new one, so Atlas (the AI Employee) can triage it.

Configuration (vault-root .env or environment variables):
    GMAIL_ADDRESS       your Gmail address
    GMAIL_APP_PASSWORD  a Google "App Password" (not your normal password)
    GMAIL_POLL_FOLDER   IMAP folder to watch (default: INBOX)

Run once per invocation (designed for Task Scheduler):
    python Watchers/gmail_watcher.py
Or loop continuously:
    python Watchers/gmail_watcher.py --loop [interval_seconds]
"""

import email
import email.header
import imaplib
import sys
import time

from vault_env import load_env, load_state, save_state, create_task_file, log
import os

STATE_NAME = "gmail_seen"
MAX_BODY_CHARS = 2000


def decode_header(value: str) -> str:
    if not value:
        return ""
    parts = email.header.decode_header(value)
    decoded = []
    for text, charset in parts:
        if isinstance(text, bytes):
            decoded.append(text.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(text)
    return " ".join(decoded)


def extract_body(msg) -> str:
    """Get the plain-text body of an email message."""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and not part.get(
                "Content-Disposition", ""
            ).startswith("attachment"):
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    return payload.decode(charset, errors="replace")
        return "(no plain-text body found)"
    payload = msg.get_payload(decode=True)
    if payload:
        charset = msg.get_content_charset() or "utf-8"
        return payload.decode(charset, errors="replace")
    return "(empty body)"


def guess_priority(subject: str, body: str) -> str:
    text = (subject + " " + body[:500]).lower()
    if any(w in text for w in ("urgent", "asap", "immediately", "emergency")):
        return "urgent"
    if any(w in text for w in ("important", "invoice", "payment", "deadline")):
        return "high"
    return "normal"


def check_gmail() -> int:
    """Poll once. Returns the number of new tasks created."""
    address = os.environ.get("GMAIL_ADDRESS")
    password = os.environ.get("GMAIL_APP_PASSWORD")
    folder = os.environ.get("GMAIL_POLL_FOLDER", "INBOX")

    if not address or not password:
        log("[gmail] Skipped: GMAIL_ADDRESS / GMAIL_APP_PASSWORD not set in .env")
        return 0

    state = load_state(STATE_NAME)
    seen_ids = set(state.get("seen_message_ids", []))
    created = 0

    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    try:
        mail.login(address, password)
        mail.select(folder, readonly=True)  # readonly: never mutate the mailbox
        status, data = mail.search(None, "UNSEEN")
        if status != "OK":
            log(f"[gmail] IMAP search failed: {status}")
            return 0

        for num in data[0].split():
            status, msg_data = mail.fetch(num, "(RFC822)")
            if status != "OK":
                continue
            msg = email.message_from_bytes(msg_data[0][1])
            message_id = msg.get("Message-ID", f"no-id-{num.decode()}")
            if message_id in seen_ids:
                continue

            subject = decode_header(msg.get("Subject", "(no subject)"))
            sender = decode_header(msg.get("From", "unknown"))
            date = msg.get("Date", "")
            body = extract_body(msg)[:MAX_BODY_CHARS]

            create_task_file(
                source="gmail",
                title=f"Email: {subject}",
                body=(
                    f"**From:** {sender}\n"
                    f"**Date:** {date}\n"
                    f"**Subject:** {subject}\n\n"
                    f"## Message\n\n{body}\n\n"
                    f"## Suggested Actions\n"
                    f"- [ ] Read and triage this email\n"
                    f"- [ ] Draft a reply (route through /Pending_Approval before sending)\n"
                    f"- [ ] Extract any action items\n"
                ),
                priority=guess_priority(subject, body),
                task_type="email",
            )
            seen_ids.add(message_id)
            created += 1
    finally:
        try:
            mail.logout()
        except Exception:
            pass

    state["seen_message_ids"] = list(seen_ids)[-500:]  # cap state size
    save_state(STATE_NAME, state)
    if created:
        log(f"[gmail] Created {created} new task(s)")
    else:
        print("[gmail] No new unread emails.")
    return created


def main():
    load_env()
    if "--loop" in sys.argv:
        idx = sys.argv.index("--loop")
        interval = int(sys.argv[idx + 1]) if len(sys.argv) > idx + 1 else 300
        print(f"[gmail] Watching every {interval}s. Ctrl+C to stop.")
        while True:
            try:
                check_gmail()
            except Exception as e:
                log(f"[gmail] ERROR: {e}")
            time.sleep(interval)
    else:
        try:
            check_gmail()
        except Exception as e:
            log(f"[gmail] ERROR: {e}")
            sys.exit(0)  # exit cleanly so Task Scheduler doesn't flag failures


if __name__ == "__main__":
    main()
