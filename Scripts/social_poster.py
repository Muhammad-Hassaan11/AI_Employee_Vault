#!/usr/bin/env python3
"""
Social media posting + summary functions for AI Employee Vault.

Supports Facebook Pages and Instagram Business (Meta Graph API) and
Twitter/X (API v2 with OAuth 1.0a user context). Pure stdlib.

Used by:
    - Scripts/approval_executor.py  (publishes human-approved posts)
    - MCP/social_server.py          (exposes tools to Claude)

Configuration (vault-root .env):
    META_PAGE_ID / META_PAGE_ACCESS_TOKEN   Facebook Page
    IG_USER_ID                              Instagram business account id
    X_API_KEY / X_API_SECRET                Twitter app consumer keys
    X_ACCESS_TOKEN / X_ACCESS_SECRET        Twitter user tokens
"""

import base64
import hashlib
import hmac
import json
import os
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "Watchers"))
from vault_env import load_env, log, audit  # noqa: E402

GRAPH = "https://graph.facebook.com/v21.0"


def _http_json(url: str, data: bytes = None, headers: dict = None,
               method: str = None) -> dict:
    req = urllib.request.Request(url, data=data, headers=headers or {},
                                 method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:400]
        raise RuntimeError(f"HTTP {e.code}: {detail}") from e


# --------------------------- Facebook -----------------------------------

def post_facebook(message: str) -> str:
    load_env()
    page_id = os.environ.get("META_PAGE_ID")
    token = os.environ.get("META_PAGE_ACCESS_TOKEN")
    if not page_id or not token:
        return "ERROR: META_PAGE_ID / META_PAGE_ACCESS_TOKEN not set in .env"
    data = urllib.parse.urlencode({"message": message, "access_token": token}).encode()
    try:
        result = _http_json(f"{GRAPH}/{page_id}/feed", data=data)
    except RuntimeError as e:
        audit("social", "post_facebook", status="failed", error=str(e)[:300])
        return f"ERROR: Facebook: {e}"
    post_id = result.get("id", "unknown")
    log(f"[social] Facebook post published: {post_id}")
    audit("social", "post_facebook", post_id=post_id)
    return f"SUCCESS: Facebook post published (id: {post_id})"


def facebook_summary(limit: int = 10) -> str:
    load_env()
    page_id = os.environ.get("META_PAGE_ID")
    token = os.environ.get("META_PAGE_ACCESS_TOKEN")
    if not page_id or not token:
        return "ERROR: META_PAGE_ID / META_PAGE_ACCESS_TOKEN not set in .env"
    params = urllib.parse.urlencode({
        "fields": "message,created_time,likes.summary(true),comments.summary(true),shares",
        "limit": str(limit),
        "access_token": token,
    })
    try:
        result = _http_json(f"{GRAPH}/{page_id}/posts?{params}")
    except RuntimeError as e:
        return f"ERROR: Facebook: {e}"
    posts = result.get("data", [])
    if not posts:
        return "Facebook: no recent posts."
    lines = [f"Facebook - last {len(posts)} post(s):"]
    total_likes = total_comments = 0
    for p in posts:
        likes = p.get("likes", {}).get("summary", {}).get("total_count", 0)
        comments = p.get("comments", {}).get("summary", {}).get("total_count", 0)
        shares = p.get("shares", {}).get("count", 0)
        total_likes += likes
        total_comments += comments
        text = (p.get("message") or "(no text)")[:80].replace("\n", " ")
        lines.append(f"- {p.get('created_time', '')[:10]} | {likes} likes, "
                     f"{comments} comments, {shares} shares | {text}")
    lines.append(f"Totals: {total_likes} likes, {total_comments} comments")
    return "\n".join(lines)


# --------------------------- Instagram ----------------------------------

def post_instagram(caption: str, image_url: str) -> str:
    """Instagram requires media: create a container from a public image URL,
    then publish it."""
    load_env()
    ig_user = os.environ.get("IG_USER_ID")
    token = os.environ.get("META_PAGE_ACCESS_TOKEN")
    if not ig_user or not token:
        return "ERROR: IG_USER_ID / META_PAGE_ACCESS_TOKEN not set in .env"
    if not image_url:
        return "ERROR: Instagram posts require an image_url (public image link)"
    try:
        container = _http_json(
            f"{GRAPH}/{ig_user}/media",
            data=urllib.parse.urlencode({
                "image_url": image_url, "caption": caption, "access_token": token,
            }).encode(),
        )
        result = _http_json(
            f"{GRAPH}/{ig_user}/media_publish",
            data=urllib.parse.urlencode({
                "creation_id": container["id"], "access_token": token,
            }).encode(),
        )
    except RuntimeError as e:
        audit("social", "post_instagram", status="failed", error=str(e)[:300])
        return f"ERROR: Instagram: {e}"
    media_id = result.get("id", "unknown")
    log(f"[social] Instagram post published: {media_id}")
    audit("social", "post_instagram", media_id=media_id)
    return f"SUCCESS: Instagram post published (id: {media_id})"


def instagram_summary(limit: int = 10) -> str:
    load_env()
    ig_user = os.environ.get("IG_USER_ID")
    token = os.environ.get("META_PAGE_ACCESS_TOKEN")
    if not ig_user or not token:
        return "ERROR: IG_USER_ID / META_PAGE_ACCESS_TOKEN not set in .env"
    params = urllib.parse.urlencode({
        "fields": "caption,timestamp,like_count,comments_count,media_type",
        "limit": str(limit),
        "access_token": token,
    })
    try:
        result = _http_json(f"{GRAPH}/{ig_user}/media?{params}")
    except RuntimeError as e:
        return f"ERROR: Instagram: {e}"
    posts = result.get("data", [])
    if not posts:
        return "Instagram: no recent posts."
    lines = [f"Instagram - last {len(posts)} post(s):"]
    total_likes = total_comments = 0
    for p in posts:
        likes = p.get("like_count", 0)
        comments = p.get("comments_count", 0)
        total_likes += likes
        total_comments += comments
        text = (p.get("caption") or "(no caption)")[:80].replace("\n", " ")
        lines.append(f"- {p.get('timestamp', '')[:10]} | {likes} likes, "
                     f"{comments} comments | {text}")
    lines.append(f"Totals: {total_likes} likes, {total_comments} comments")
    return "\n".join(lines)


# --------------------------- Twitter / X --------------------------------

def _oauth1_header(method: str, url: str) -> str:
    """Build an OAuth 1.0a Authorization header (HMAC-SHA1) for X API v2."""
    consumer_key = os.environ["X_API_KEY"]
    consumer_secret = os.environ["X_API_SECRET"]
    token = os.environ["X_ACCESS_TOKEN"]
    token_secret = os.environ["X_ACCESS_SECRET"]

    oauth = {
        "oauth_consumer_key": consumer_key,
        "oauth_nonce": secrets.token_hex(16),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": token,
        "oauth_version": "1.0",
    }
    quote = lambda s: urllib.parse.quote(s, safe="")  # noqa: E731
    param_str = "&".join(f"{quote(k)}={quote(v)}" for k, v in sorted(oauth.items()))
    base = f"{method}&{quote(url)}&{quote(param_str)}"
    key = f"{quote(consumer_secret)}&{quote(token_secret)}"
    sig = base64.b64encode(
        hmac.new(key.encode(), base.encode(), hashlib.sha1).digest()
    ).decode()
    oauth["oauth_signature"] = sig
    return "OAuth " + ", ".join(f'{quote(k)}="{quote(v)}"' for k, v in sorted(oauth.items()))


def post_tweet(text: str) -> str:
    load_env()
    required = ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET")
    if not all(os.environ.get(k) for k in required):
        return "ERROR: X_API_KEY / X_API_SECRET / X_ACCESS_TOKEN / X_ACCESS_SECRET not set in .env"
    if len(text) > 280:
        return f"ERROR: tweet is {len(text)} chars (max 280)"
    url = "https://api.twitter.com/2/tweets"
    try:
        result = _http_json(
            url,
            data=json.dumps({"text": text}).encode(),
            headers={"Authorization": _oauth1_header("POST", url),
                     "Content-Type": "application/json"},
        )
    except RuntimeError as e:
        audit("social", "post_tweet", status="failed", error=str(e)[:300])
        return f"ERROR: X/Twitter: {e}"
    tweet_id = result.get("data", {}).get("id", "unknown")
    log(f"[social] Tweet published: {tweet_id}")
    audit("social", "post_tweet", tweet_id=tweet_id)
    return f"SUCCESS: Tweet published (id: {tweet_id})"


def twitter_summary(limit: int = 10) -> str:
    load_env()
    required = ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET")
    if not all(os.environ.get(k) for k in required):
        return "ERROR: X credentials not set in .env"
    # Resolve own user id, then fetch recent tweets with metrics
    me_url = "https://api.twitter.com/2/users/me"
    try:
        me = _http_json(me_url, headers={"Authorization": _oauth1_header("GET", me_url)})
        user_id = me["data"]["id"]
        tl_url = f"https://api.twitter.com/2/users/{user_id}/tweets"
        params = urllib.parse.urlencode({
            "max_results": str(max(5, min(limit, 100))),
            "tweet.fields": "created_at,public_metrics",
        })
        # OAuth1 signature must not include query params in base URL for this helper,
        # so sign the bare URL and pass params via the signed URL consistently:
        full_url = f"{tl_url}?{params}"
        result = _http_json(full_url, headers={
            "Authorization": _oauth1_header_with_params("GET", tl_url, params)})
    except RuntimeError as e:
        return f"ERROR: X/Twitter: {e}"
    tweets = result.get("data", [])
    if not tweets:
        return "X/Twitter: no recent tweets."
    lines = [f"X/Twitter - last {len(tweets)} tweet(s):"]
    total_likes = total_rts = 0
    for t in tweets:
        m = t.get("public_metrics", {})
        total_likes += m.get("like_count", 0)
        total_rts += m.get("retweet_count", 0)
        text = t.get("text", "")[:80].replace("\n", " ")
        lines.append(f"- {t.get('created_at', '')[:10]} | {m.get('like_count', 0)} likes, "
                     f"{m.get('retweet_count', 0)} RTs, {m.get('impression_count', 0)} views | {text}")
    lines.append(f"Totals: {total_likes} likes, {total_rts} retweets")
    return "\n".join(lines)


def _oauth1_header_with_params(method: str, base_url: str, encoded_params: str) -> str:
    """OAuth 1.0a header including query parameters in the signature base."""
    consumer_key = os.environ["X_API_KEY"]
    consumer_secret = os.environ["X_API_SECRET"]
    token = os.environ["X_ACCESS_TOKEN"]
    token_secret = os.environ["X_ACCESS_SECRET"]

    oauth = {
        "oauth_consumer_key": consumer_key,
        "oauth_nonce": secrets.token_hex(16),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": token,
        "oauth_version": "1.0",
    }
    query = dict(urllib.parse.parse_qsl(encoded_params))
    all_params = {**oauth, **query}
    quote = lambda s: urllib.parse.quote(str(s), safe="")  # noqa: E731
    param_str = "&".join(f"{quote(k)}={quote(v)}" for k, v in sorted(all_params.items()))
    base = f"{method}&{quote(base_url)}&{quote(param_str)}"
    key = f"{quote(consumer_secret)}&{quote(token_secret)}"
    sig = base64.b64encode(
        hmac.new(key.encode(), base.encode(), hashlib.sha1).digest()
    ).decode()
    oauth["oauth_signature"] = sig
    return "OAuth " + ", ".join(f'{quote(k)}="{quote(v)}"' for k, v in sorted(oauth.items()))


def social_summary() -> str:
    """Cross-platform engagement summary with graceful degradation:
    unconfigured/failed platforms report their status instead of aborting."""
    sections = []
    for name, fn in (("Facebook", facebook_summary),
                     ("Instagram", instagram_summary),
                     ("X/Twitter", twitter_summary)):
        try:
            sections.append(fn())
        except Exception as e:  # noqa: BLE001
            sections.append(f"{name}: unavailable ({e})")
    return "\n\n".join(sections)


if __name__ == "__main__":
    load_env()
    print(social_summary())
