#!/usr/bin/env python3
"""
Social Media MCP Server for AI Employee Vault.

A stdio MCP server (pure stdlib) exposing Facebook Page, Instagram
Business and Twitter/X tools backed by Scripts/social_poster.py.

Read tools (safe, no approval needed):
    social_health, facebook_summary, instagram_summary,
    twitter_summary, social_summary
Write tools (SENSITIVE - human approval required):
    post_facebook, post_instagram, post_tweet
    Each takes an `approved` flag. Per the Company Handbook, Atlas must
    NEVER call these with approved=true directly; instead it drafts an
    action file in /Pending_Approval and the approval executor (which a
    human has gated) publishes it. approved=false returns instructions.

Configuration (vault-root .env):
    META_PAGE_ID / META_PAGE_ACCESS_TOKEN   Facebook Page
    IG_USER_ID                              Instagram business account id
    X_API_KEY / X_API_SECRET                Twitter app consumer keys
    X_ACCESS_TOKEN / X_ACCESS_SECRET        Twitter user tokens
"""

import json
import os
import sys
from pathlib import Path

VAULT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(VAULT_ROOT / "Scripts"))
sys.path.insert(0, str(VAULT_ROOT / "Watchers"))

import social_poster  # noqa: E402
from vault_env import load_env, audit  # noqa: E402

PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "vault-social", "version": "1.0.0"}

APPROVAL_HINT = (
    "BLOCKED: publishing to social media is a sensitive action. "
    "Write an action file to /Pending_Approval with frontmatter "
    "(type: {atype}, status: pending) and the post text as the body. "
    "A human flips status to approved and the approval executor publishes it."
)

TOOLS = [
    {
        "name": "social_health",
        "description": "Report which social platforms (Facebook, Instagram, X/Twitter) have credentials configured in .env.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "facebook_summary",
        "description": "Engagement summary of recent Facebook Page posts (likes, comments, shares).",
        "inputSchema": {
            "type": "object",
            "properties": {"limit": {"type": "integer", "description": "Max posts (default 10)"}},
        },
    },
    {
        "name": "instagram_summary",
        "description": "Engagement summary of recent Instagram posts (likes, comments).",
        "inputSchema": {
            "type": "object",
            "properties": {"limit": {"type": "integer", "description": "Max posts (default 10)"}},
        },
    },
    {
        "name": "twitter_summary",
        "description": "Engagement summary of recent X/Twitter posts (likes, retweets, views).",
        "inputSchema": {
            "type": "object",
            "properties": {"limit": {"type": "integer", "description": "Max tweets (default 10)"}},
        },
    },
    {
        "name": "social_summary",
        "description": "Cross-platform engagement summary (Facebook + Instagram + X). Unconfigured platforms degrade gracefully. Used by the weekly audit / CEO briefing.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "post_facebook",
        "description": "Publish a post to the Facebook Page. SENSITIVE: requires prior human approval via /Pending_Approval; never call with approved=true on your own.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "message": {"type": "string"},
                "approved": {"type": "boolean", "description": "Must be true, only after human approval"},
            },
            "required": ["message"],
        },
    },
    {
        "name": "post_instagram",
        "description": "Publish an image post to Instagram Business. SENSITIVE: requires prior human approval via /Pending_Approval.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "caption": {"type": "string"},
                "image_url": {"type": "string", "description": "Public URL of the image"},
                "approved": {"type": "boolean"},
            },
            "required": ["caption", "image_url"],
        },
    },
    {
        "name": "post_tweet",
        "description": "Publish a tweet (max 280 chars) on X/Twitter. SENSITIVE: requires prior human approval via /Pending_Approval.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "approved": {"type": "boolean"},
            },
            "required": ["text"],
        },
    },
]


def _configured(*keys) -> bool:
    return all(os.environ.get(k) for k in keys)


def tool_social_health(args: dict) -> str:
    load_env()
    lines = ["Social platform configuration:"]
    lines.append("- Facebook: " + ("configured" if _configured("META_PAGE_ID", "META_PAGE_ACCESS_TOKEN") else "NOT configured (META_PAGE_ID / META_PAGE_ACCESS_TOKEN)"))
    lines.append("- Instagram: " + ("configured" if _configured("IG_USER_ID", "META_PAGE_ACCESS_TOKEN") else "NOT configured (IG_USER_ID / META_PAGE_ACCESS_TOKEN)"))
    lines.append("- X/Twitter: " + ("configured" if _configured("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET") else "NOT configured (X_API_KEY / X_API_SECRET / X_ACCESS_TOKEN / X_ACCESS_SECRET)"))
    return "\n".join(lines)


def _gated(atype: str, approved, publish):
    if not approved:
        audit("social-mcp", f"{atype}_blocked", status="blocked")
        return APPROVAL_HINT.format(atype=atype)
    return publish()


HANDLERS = {
    "social_health": tool_social_health,
    "facebook_summary": lambda a: social_poster.facebook_summary(int(a.get("limit", 10))),
    "instagram_summary": lambda a: social_poster.instagram_summary(int(a.get("limit", 10))),
    "twitter_summary": lambda a: social_poster.twitter_summary(int(a.get("limit", 10))),
    "social_summary": lambda a: social_poster.social_summary(),
    "post_facebook": lambda a: _gated("facebook_post", a.get("approved"),
                                      lambda: social_poster.post_facebook(a["message"])),
    "post_instagram": lambda a: _gated("instagram_post", a.get("approved"),
                                       lambda: social_poster.post_instagram(a["caption"], a["image_url"])),
    "post_tweet": lambda a: _gated("tweet", a.get("approved"),
                                   lambda: social_poster.post_tweet(a["text"])),
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
                load_env()
                text = handler(args)
            except Exception as e:  # graceful degradation: report, don't crash
                text = f"ERROR: {e}"
                audit("social-mcp", name, status="failed", error=str(e)[:300])
        result = {"content": [{"type": "text", "text": text}],
                  "isError": text.startswith(("ERROR", "BLOCKED"))}
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
