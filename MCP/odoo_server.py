#!/usr/bin/env python3
"""
Odoo Accounting MCP Server for AI Employee Vault.

A stdio MCP server (pure stdlib) that talks to a self-hosted Odoo
Community 19 instance over its JSON-RPC API (/jsonrpc, service
common.authenticate + object.execute_kw).

Read tools (safe, no approval needed):
    list_invoices, list_expenses, accounting_summary, list_customers
Write tools:
    create_customer, create_draft_invoice  - create DRAFT records only
    (posting/validating invoices or registering payments is deliberately
    not exposed; per the Company Handbook those need human action in Odoo)

Configuration (vault-root .env):
    ODOO_URL       e.g. http://localhost:8069
    ODOO_DB        database name, e.g. business
    ODOO_USER      login email, e.g. admin
    ODOO_PASSWORD  password or API key
"""

import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

VAULT_ROOT = Path(__file__).parent.parent.resolve()
PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "vault-odoo", "version": "1.0.0"}

TOOLS = [
    {
        "name": "odoo_health",
        "description": "Check connectivity and authentication to the Odoo server.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "list_invoices",
        "description": "List customer invoices (account.move, out_invoice) with number, partner, date, total, state and payment state.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Max records (default 20)"},
                "days": {"type": "integer", "description": "Only invoices from the last N days (default 90)"},
            },
        },
    },
    {
        "name": "list_expenses",
        "description": "List vendor bills / expenses (account.move, in_invoice) with vendor, date, total and state.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Max records (default 20)"},
                "days": {"type": "integer", "description": "Only bills from the last N days (default 90)"},
            },
        },
    },
    {
        "name": "accounting_summary",
        "description": "Summarize the last N days: revenue invoiced, expenses billed, amounts still unpaid, invoice counts. Used for the weekly audit / CEO briefing.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Period length in days (default 7)"}
            },
        },
    },
    {
        "name": "list_customers",
        "description": "List customers (res.partner where customer_rank > 0).",
        "inputSchema": {
            "type": "object",
            "properties": {"limit": {"type": "integer", "description": "Max records (default 20)"}},
        },
    },
    {
        "name": "create_customer",
        "description": "Create a customer contact (res.partner).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "email": {"type": "string"},
                "phone": {"type": "string"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "create_draft_invoice",
        "description": "Create a DRAFT customer invoice (never posted automatically - a human reviews and posts it in Odoo).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "integer", "description": "res.partner id (from list_customers)"},
                "description": {"type": "string", "description": "Invoice line description"},
                "amount": {"type": "number", "description": "Line amount (untaxed)"},
            },
            "required": ["customer_id", "description", "amount"],
        },
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


def audit(action: str, status: str = "ok", **details):
    logs_dir = VAULT_ROOT / "Logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    entry = {"ts": datetime.now().isoformat(timespec="seconds"),
             "component": "odoo-mcp", "action": action, "status": status}
    if details:
        entry["details"] = details
    with open(logs_dir / "audit.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


class OdooClient:
    def __init__(self):
        self.url = os.environ.get("ODOO_URL", "http://localhost:8069").rstrip("/")
        self.db = os.environ.get("ODOO_DB", "business")
        self.user = os.environ.get("ODOO_USER", "admin")
        self.password = os.environ.get("ODOO_PASSWORD", "")
        self._uid = None

    def _rpc(self, service: str, method: str, args: list):
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {"service": service, "method": method, "args": args},
            "id": 1,
        }
        req = urllib.request.Request(
            f"{self.url}/jsonrpc",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if data.get("error"):
            msg = data["error"].get("data", {}).get("message") or data["error"].get("message")
            raise RuntimeError(f"Odoo error: {msg}")
        return data.get("result")

    def uid(self):
        if self._uid is None:
            self._uid = self._rpc("common", "authenticate",
                                  [self.db, self.user, self.password, {}])
            if not self._uid:
                raise RuntimeError("Odoo authentication failed (check ODOO_USER/ODOO_PASSWORD/ODOO_DB)")
        return self._uid

    def execute(self, model: str, method: str, args: list, kwargs: dict = None):
        return self._rpc("object", "execute_kw",
                         [self.db, self.uid(), self.password,
                          model, method, args, kwargs or {}])


def fmt_money(value) -> str:
    try:
        return f"{float(value):,.2f}"
    except (TypeError, ValueError):
        return str(value)


def moves_domain(move_type: str, days: int):
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    return [["move_type", "=", move_type], ["invoice_date", ">=", since]]


def tool_odoo_health(client: OdooClient, args: dict) -> str:
    version = client._rpc("common", "version", [])
    uid = client.uid()
    return (f"OK: connected to Odoo {version.get('server_version')} at {client.url}, "
            f"db '{client.db}', authenticated as uid {uid}")


def tool_list_moves(client: OdooClient, args: dict, move_type: str, label: str) -> str:
    limit = int(args.get("limit", 20))
    days = int(args.get("days", 90))
    records = client.execute(
        "account.move", "search_read",
        [moves_domain(move_type, days)],
        {"fields": ["name", "partner_id", "invoice_date", "amount_total",
                    "state", "payment_state"],
         "limit": limit, "order": "invoice_date desc"},
    )
    if not records:
        return f"No {label} in the last {days} days."
    lines = [f"{label.capitalize()} (last {days} days):"]
    for r in records:
        partner = r["partner_id"][1] if r.get("partner_id") else "?"
        lines.append(f"- {r.get('name') or 'draft'} | {partner} | "
                     f"{r.get('invoice_date')} | {fmt_money(r.get('amount_total'))} | "
                     f"{r.get('state')}/{r.get('payment_state')}")
    return "\n".join(lines)


def tool_accounting_summary(client: OdooClient, args: dict) -> str:
    days = int(args.get("days", 7))

    def totals(move_type):
        recs = client.execute(
            "account.move", "search_read",
            [moves_domain(move_type, days)],
            {"fields": ["amount_total", "amount_residual", "state"]},
        )
        posted = [r for r in recs if r["state"] == "posted"]
        return {
            "count": len(recs),
            "posted": len(posted),
            "total": sum(r["amount_total"] for r in posted),
            "unpaid": sum(r.get("amount_residual") or 0 for r in posted),
        }

    inv = totals("out_invoice")
    bills = totals("in_invoice")
    net = inv["total"] - bills["total"]
    return (
        f"Accounting summary - last {days} days\n"
        f"Revenue: {fmt_money(inv['total'])} across {inv['posted']} posted invoice(s) "
        f"({inv['count']} total incl. drafts); outstanding receivables {fmt_money(inv['unpaid'])}\n"
        f"Expenses: {fmt_money(bills['total'])} across {bills['posted']} posted bill(s) "
        f"({bills['count']} total); unpaid payables {fmt_money(bills['unpaid'])}\n"
        f"Net (invoiced - billed): {fmt_money(net)}"
    )


def tool_list_customers(client: OdooClient, args: dict) -> str:
    limit = int(args.get("limit", 20))
    records = client.execute(
        "res.partner", "search_read",
        [[["customer_rank", ">", 0]]],
        {"fields": ["id", "name", "email", "phone"], "limit": limit},
    )
    if not records:
        return "No customers yet."
    return "Customers:\n" + "\n".join(
        f"- [{r['id']}] {r['name']} | {r.get('email') or '-'} | {r.get('phone') or '-'}"
        for r in records
    )


def tool_create_customer(client: OdooClient, args: dict) -> str:
    vals = {"name": args["name"], "customer_rank": 1}
    if args.get("email"):
        vals["email"] = args["email"]
    if args.get("phone"):
        vals["phone"] = args["phone"]
    new_id = client.execute("res.partner", "create", [vals])
    audit("create_customer", name=args["name"], id=new_id)
    return f"SUCCESS: customer '{args['name']}' created with id {new_id}"


def tool_create_draft_invoice(client: OdooClient, args: dict) -> str:
    vals = {
        "move_type": "out_invoice",
        "partner_id": int(args["customer_id"]),
        "invoice_date": datetime.now().strftime("%Y-%m-%d"),
        "invoice_line_ids": [(0, 0, {
            "name": args["description"],
            "quantity": 1,
            "price_unit": float(args["amount"]),
        })],
    }
    new_id = client.execute("account.move", "create", [vals])
    audit("create_draft_invoice", invoice_id=new_id,
          customer_id=args["customer_id"], amount=args["amount"])
    return (f"SUCCESS: draft invoice id {new_id} created for "
            f"{fmt_money(args['amount'])} - review and post it in Odoo")


HANDLERS = {
    "odoo_health": tool_odoo_health,
    "list_invoices": lambda c, a: tool_list_moves(c, a, "out_invoice", "customer invoices"),
    "list_expenses": lambda c, a: tool_list_moves(c, a, "in_invoice", "vendor bills"),
    "accounting_summary": tool_accounting_summary,
    "list_customers": tool_list_customers,
    "create_customer": tool_create_customer,
    "create_draft_invoice": tool_create_draft_invoice,
}


def handle_request(req: dict):
    method = req.get("method")
    req_id = req.get("id")
    params = req.get("params", {})

    if method == "initialize":
        result = {"protocolVersion": PROTOCOL_VERSION,
                  "capabilities": {"tools": {}}, "serverInfo": SERVER_INFO}
    elif method == "tools/list":
        result = {"tools": TOOLS}
    elif method == "tools/call":
        name = params.get("name")
        args = params.get("arguments", {})
        handler = HANDLERS.get(name)
        if handler is None:
            text = f"ERROR: unknown tool {name}"
        else:
            try:
                text = handler(OdooClient(), args)
            except Exception as e:  # graceful degradation: report, don't crash
                text = f"ERROR: {e}"
                audit(name, status="failed", error=str(e)[:300])
        result = {"content": [{"type": "text", "text": text}],
                  "isError": text.startswith("ERROR")}
    elif method == "ping":
        result = {}
    elif req_id is None:
        return None
    else:
        return {"jsonrpc": "2.0", "id": req_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"}}

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
