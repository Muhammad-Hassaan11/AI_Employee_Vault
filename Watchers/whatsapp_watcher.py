#!/usr/bin/env python3
"""
WhatsApp Watcher for AI Employee Vault.

Polls the Twilio WhatsApp API for new inbound messages and creates a task
file in /Needs_Action for each one. Uses only the Python standard library.

Configuration (vault-root .env or environment variables):
    TWILIO_ACCOUNT_SID    Twilio account SID
    TWILIO_AUTH_TOKEN     Twilio auth token
    TWILIO_WHATSAPP_TO    your WhatsApp-enabled Twilio number, e.g. +14155238886

Run once (for Task Scheduler):
    python Watchers/whatsapp_watcher.py
Loop mode:
    python Watchers/whatsapp_watcher.py --loop [interval_seconds]
"""

import base64
import json
import os
import sys
import time
import urllib.parse
import urllib.request

from vault_env import load_env, load_state, save_state, create_task_file, log

STATE_NAME = "whatsapp_seen"


def guess_priority(body: str) -> str:
    text = body.lower()
    if any(w in text for w in ("urgent", "asap", "emergency", "now")):
        return "urgent"
    if any(w in text for w in ("today", "important", "payment", "order")):
        return "high"
    return "normal"


def fetch_messages(sid: str, token: str, to_number: str) -> list:
    """Fetch recent inbound WhatsApp messages from the Twilio REST API."""
    params = urllib.parse.urlencode(
        {"To": f"whatsapp:{to_number}", "PageSize": "50"}
    )
    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json?{params}"
    auth = base64.b64encode(f"{sid}:{token}".encode()).decode()
    req = urllib.request.Request(url, headers={"Authorization": f"Basic {auth}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    # Only inbound messages (sent to us, not by us)
    return [m for m in data.get("messages", []) if m.get("direction") == "inbound"]


def check_whatsapp() -> int:
    sid = os.environ.get("TWILIO_ACCOUNT_SID")
    token = os.environ.get("TWILIO_AUTH_TOKEN")
    to_number = os.environ.get("TWILIO_WHATSAPP_TO")

    if not sid or not token or not to_number:
        log("[whatsapp] Skipped: TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN / "
            "TWILIO_WHATSAPP_TO not set in .env")
        return 0

    state = load_state(STATE_NAME)
    seen_sids = set(state.get("seen_message_sids", []))
    created = 0

    for msg in fetch_messages(sid, token, to_number):
        msg_sid = msg.get("sid")
        if not msg_sid or msg_sid in seen_sids:
            continue

        sender = msg.get("from", "unknown").replace("whatsapp:", "")
        body = msg.get("body", "(no text)")
        date_sent = msg.get("date_sent", "")

        create_task_file(
            source="whatsapp",
            title=f"WhatsApp from {sender}",
            body=(
                f"**From:** {sender}\n"
                f"**Received:** {date_sent}\n\n"
                f"## Message\n\n{body}\n\n"
                f"## Suggested Actions\n"
                f"- [ ] Read and triage this message\n"
                f"- [ ] Draft a reply (route through /Pending_Approval before sending)\n"
            ),
            priority=guess_priority(body),
            task_type="whatsapp",
        )
        seen_sids.add(msg_sid)
        created += 1

    state["seen_message_sids"] = list(seen_sids)[-500:]
    save_state(STATE_NAME, state)
    if created:
        log(f"[whatsapp] Created {created} new task(s)")
    else:
        print("[whatsapp] No new messages.")
    return created


def main():
    load_env()
    if "--loop" in sys.argv:
        idx = sys.argv.index("--loop")
        interval = int(sys.argv[idx + 1]) if len(sys.argv) > idx + 1 else 300
        print(f"[whatsapp] Watching every {interval}s. Ctrl+C to stop.")
        while True:
            try:
                check_whatsapp()
            except Exception as e:
                log(f"[whatsapp] ERROR: {e}")
            time.sleep(interval)
    else:
        try:
            check_whatsapp()
        except Exception as e:
            log(f"[whatsapp] ERROR: {e}")
            sys.exit(0)


if __name__ == "__main__":
    main()
