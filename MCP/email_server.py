#!/usr/bin/env python3
"""
Email MCP Server for AI Employee Vault.

A stdio Model Context Protocol server (pure stdlib, no dependencies) that
exposes tools for sending email via SMTP. Registered in the vault's
.mcp.json so Claude Code can call it directly.

Safety: send_email refuses to send unless approved=true is passed, which
the AI Employee may only set after a human has approved the draft in
/Pending_Approval (see Company_Handbook.md).

Configuration (vault-root .env or environment variables):
    SMTP_HOST      e.g. smtp.gmail.com
    SMTP_PORT      e.g. 587
    SMTP_USER      sender address (e.g. your Gmail)
    SMTP_PASSWORD  app password
"""

import json
import os
import smtplib
import sys
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

VAULT_ROOT = Path(__file__).parent.parent.resolve()

PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "vault-email", "version": "1.0.0"}

TOOLS = [
    {
        "name": "send_email",
        "description": (
            "Send an email via SMTP. Requires approved=true, which may only "
            "be set after a human has approved the draft in /Pending_Approval."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient email address"},
                "subject": {"type": "string", "description": "Email subject"},
                "body": {"type": "string", "description": "Plain-text email body"},
                "approved": {
                    "type": "boolean",
                    "description": "Must be true; set only after human approval",
                },
            },
            "required": ["to", "subject", "body", "approved"],
        },
    },
    {
        "name": "check_smtp_config",
        "description": "Check whether SMTP credentials are configured (does not send anything).",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


def load_env():
    env_file = VAULT_ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def log_action(message: str) -> None:
    logs_dir = VAULT_ROOT / "Logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now()
    with open(logs_dir / f"{now.strftime('%Y-%m-%d')}.md", "a", encoding="utf-8") as f:
        f.write(f"- {now.strftime('%H:%M:%S')} [email-mcp] {message}\n")


def send_email(to: str, subject: str, body: str, approved: bool) -> str:
    if not approved:
        return (
            "REFUSED: approved must be true. Route this email through "
            "/Pending_Approval and get human approval first."
        )
    host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASSWORD")
    if not user or not password:
        return "ERROR: SMTP_USER / SMTP_PASSWORD not configured in .env"

    msg = MIMEMultipart()
    msg["From"] = user
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    with smtplib.SMTP(host, port, timeout=30) as server:
        server.starttls()
        server.login(user, password)
        server.sendmail(user, [to], msg.as_string())

    log_action(f"Sent email to {to}: {subject}")
    return f"SUCCESS: Email sent to {to} (subject: {subject})"


def check_smtp_config() -> str:
    user = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASSWORD")
    host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    if user and password:
        return f"SMTP configured: {user} via {host}"
    return "SMTP NOT configured: set SMTP_USER and SMTP_PASSWORD in .env"


def handle_request(req: dict):
    """Return a response dict, or None for notifications."""
    method = req.get("method")
    req_id = req.get("id")
    params = req.get("params", {})

    if method == "initialize":
        result = {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": SERVER_INFO,
        }
    elif method == "tools/list":
        result = {"tools": TOOLS}
    elif method == "tools/call":
        name = params.get("name")
        args = params.get("arguments", {})
        try:
            if name == "send_email":
                text = send_email(
                    args.get("to", ""),
                    args.get("subject", ""),
                    args.get("body", ""),
                    bool(args.get("approved", False)),
                )
            elif name == "check_smtp_config":
                text = check_smtp_config()
            else:
                text = f"ERROR: unknown tool {name}"
        except Exception as e:
            text = f"ERROR: {e}"
        result = {
            "content": [{"type": "text", "text": text}],
            "isError": text.startswith(("ERROR", "REFUSED")),
        }
    elif method == "ping":
        result = {}
    elif req_id is None:
        return None  # notification (e.g. notifications/initialized) - no reply
    else:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"},
        }

    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def main():
    load_env()
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        resp = handle_request(req)
        if resp is not None:
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
