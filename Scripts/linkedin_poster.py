#!/usr/bin/env python3
"""
LinkedIn Poster for AI Employee Vault.

Publishes a text post to LinkedIn via the official REST API (ugcPosts).
Called by Scripts/approval_executor.py for posts a human has approved -
never call this with unapproved content.

Configuration (vault-root .env or environment variables):
    LINKEDIN_ACCESS_TOKEN  OAuth token with the w_member_social scope
    LINKEDIN_PERSON_URN    e.g. urn:li:person:AbC123xYz
                           (from GET https://api.linkedin.com/v2/userinfo -> sub)

Manual test:
    python Scripts/linkedin_poster.py "Hello from Atlas"
"""

import json
import os
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "Watchers"))
from vault_env import load_env, log  # noqa: E402

API_URL = "https://api.linkedin.com/v2/ugcPosts"


def post_to_linkedin(text: str) -> str:
    """Publish a text share. Returns 'SUCCESS: ...' or 'ERROR: ...'."""
    load_env()
    token = os.environ.get("LINKEDIN_ACCESS_TOKEN")
    person_urn = os.environ.get("LINKEDIN_PERSON_URN")
    if not token or not person_urn:
        return ("ERROR: LINKEDIN_ACCESS_TOKEN / LINKEDIN_PERSON_URN not set "
                "in .env - cannot publish")

    payload = {
        "author": person_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text},
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        },
    }
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            post_id = resp.headers.get("x-restli-id", "unknown")
            log(f"[linkedin] Published post {post_id}")
            return f"SUCCESS: LinkedIn post published (id: {post_id})"
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:300]
        return f"ERROR: LinkedIn API {e.code}: {detail}"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python linkedin_poster.py \"post text\"")
        sys.exit(1)
    print(post_to_linkedin(sys.argv[1]))
