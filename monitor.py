#!/usr/bin/env python3
"""
Coding Agent Monitor

Monitors GitHub release pages of AI coding CLI tools daily and sends
Discord notifications when a new version is published.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import pytz
import requests


# Constants
GITHUB_API_BASE = "https://api.github.com/repos"
DISCORD_MAX_LENGTH = 2000
DISCORD_SPLIT_MARGIN = 100  # Leave room for safety
RELEASE_NOTES_TRUNCATE = 800
SCRIPT_DIR = Path(__file__).parent.resolve()
VERSIONS_FILE = SCRIPT_DIR / "versions.json"
RELEASES_FILE = SCRIPT_DIR / "RELEASES.md"
WATCHLIST_FILE = SCRIPT_DIR / "watchlist.json"

# Timezone for display
TZ_HKT = pytz.timezone("Asia/Hong_Kong")


def load_watchlist():
    """Load the watchlist configuration."""
    with open(WATCHLIST_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def fetch_latest_release(owner, repo):
    """
    Fetch the latest release info from GitHub API.

    Returns dict with tag_name, name, published_at, html_url, body
    or None on error.
    """
    url = f"{GITHUB_API_BASE}/{owner}/{repo}/releases/latest"
    headers = {"Accept": "application/vnd.github+json"}

    # Use token if available for higher rate limit
    github_token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()

        return {
            "tag_name": data.get("tag_name", "unknown"),
            "name": data.get("name", data.get("tag_name", "Untitled")),
            "published_at": data.get("published_at", ""),
            "html_url": data.get("html_url", ""),
            "body": data.get("body", ""),
        }
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {owner}/{repo}: {e}", file=sys.stderr)
        return None


def load_versions():
    """Load persisted versions from versions.json."""
    if not VERSIONS_FILE.exists():
        return {}

    try:
        with open(VERSIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def save_versions(versions):
    """Save versions to versions.json."""
    with open(VERSIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(versions, f, indent=2)
        f.write("\n")


def detect_changes(watchlist, fetched_versions, stored_versions):
    """
    Compare fetched versions against stored versions.

    Returns list of (tool_id, old_tag, new_release_data) tuples.
    """
    changes = []

    for tool in watchlist:
        tool_id = tool["id"]
        if tool_id not in fetched_versions:
            continue

        fetched = fetched_versions[tool_id]
        stored = stored_versions.get(tool_id, {})

        old_tag = stored.get("tag", None)
        new_tag = fetched.get("tag_name")

        # Skip if no change
        if old_tag == new_tag:
            continue

        # First run: record but don't alert
        if old_tag is None:
            continue

        changes.append((tool_id, old_tag, fetched))

    return changes


def is_first_run(stored_versions, watchlist):
    """Check if this is the first run (no versions stored)."""
    if not stored_versions:
        return True

    # Check if all watched tools have stored versions
    for tool in watchlist:
        if tool["id"] not in stored_versions:
            return True

    return False


def format_timestamp_gmt8(iso_timestamp):
    """Convert ISO timestamp to GMT+8 formatted string."""
    if not iso_timestamp:
        return "Unknown"

    try:
        # Parse ISO format
        dt = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
        # Convert to HKT (GMT+8)
        dt_hkt = dt.astimezone(TZ_HKT)
        return dt_hkt.strftime("%Y-%m-%d %H:%M:%S HKT")
    except (ValueError, AttributeError):
        return iso_timestamp


def build_alert_message(tool, old_tag, new_release):
    """Build Discord alert message for a new release."""
    emoji = tool.get("emoji", "📦")
    tool_name = tool["id"]
    new_tag = new_release.get("tag_name", "unknown")
    release_name = new_release.get("name", new_tag)
    published_at = format_timestamp_gmt8(new_release.get("published_at", ""))
    html_url = new_release.get("html_url", "")

    # Truncate release notes
    body = new_release.get("body", "")
    if len(body) > RELEASE_NOTES_TRUNCATE:
        body = body[:RELEASE_NOTES_TRUNCATE] + "..."

    # Build message
    lines = [
        f"{emoji} **New Release: {tool_name}**",
        f"",
        f"**Version:** `{old_tag}` → `{new_tag}`",
        f"**Release:** {release_name}",
        f"**Published:** {published_at}",
        f"**Link:** {html_url}",
        f"",
        f"**Release Notes:**",
        f"```",
        body if body else "(No release notes)",
        f"```",
    ]

    return "\n".join(lines)


def build_status_message(watchlist, fetched_versions):
    """Build quiet daily status message when no changes detected."""
    lines = ["📊 **Daily Status Report**", ""]

    for tool in watchlist:
        tool_id = tool["id"]
        emoji = tool.get("emoji", "📦")
        fetched = fetched_versions.get(tool_id, {})
        tag = fetched.get("tag_name", "unknown")
        published = format_timestamp_gmt8(fetched.get("published_at", ""))

        lines.append(f"{emoji} **{tool_id}**: `{tag}` ({published})")

    lines.append("")
    lines.append("No new releases detected today.")

    return "\n".join(lines)


def build_initial_message(watchlist, fetched_versions):
    """Build first-run setup confirmation message."""
    lines = ["✅ **Monitor Initialized**", ""]
    lines.append("Now tracking the following tools:")
    lines.append("")

    for tool in watchlist:
        tool_id = tool["id"]
        emoji = tool.get("emoji", "📦")
        fetched = fetched_versions.get(tool_id, {})
        tag = fetched.get("tag_name", "unknown")
        published = format_timestamp_gmt8(fetched.get("published_at", ""))

        lines.append(f"{emoji} **{tool_id}**: `{tag}` (since {published})")

    lines.append("")
    lines.append("You will be notified when new releases are published.")

    return "\n".join(lines)


def send_discord_message(content):
    """
    Send message to Discord webhook.

    Splits content if it exceeds Discord's character limit.
    """
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print("Warning: DISCORD_WEBHOOK_URL not set, skipping Discord notification", file=sys.stderr)
        return

    # Split content if needed
    chunks = []
    remaining = content

    while remaining:
        if len(remaining) <= DISCORD_MAX_LENGTH - DISCORD_SPLIT_MARGIN:
            chunks.append(remaining)
            break

        # Find a good split point (newline)
        split_point = remaining.rfind("\n", 0, DISCORD_MAX_LENGTH - DISCORD_SPLIT_MARGIN)
        if split_point == -1:
            split_point = DISCORD_MAX_LENGTH - DISCORD_SPLIT_MARGIN

        chunks.append(remaining[:split_point])
        remaining = remaining[split_point:].lstrip()

    # Send each chunk
    for chunk in chunks:
        payload = {"content": chunk}
        try:
            response = requests.post(webhook_url, json=payload, timeout=30)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Error sending Discord message: {e}", file=sys.stderr)


def update_markdown(watchlist, fetched_versions):
    """Generate RELEASES.md with current versions table."""
    now_hkt = datetime.now(TZ_HKT).strftime("%Y-%m-%d %H:%M:%S HKT")

    lines = [
        "# 📦 AI Coding Tools Release Tracker",
        "",
        f"*Last updated: {now_hkt}*",
        "",
        "| Tool | Current Version | Release Date | Link |",
        "|------|-----------------|--------------|------|",
    ]

    for tool in watchlist:
        tool_id = tool["id"]
        emoji = tool.get("emoji", "📦")
        fetched = fetched_versions.get(tool_id, {})
        tag = fetched.get("tag_name", "unknown")
        published = format_timestamp_gmt8(fetched.get("published_at", ""))
        html_url = fetched.get("html_url", "")

        display_name = f"{emoji} {tool_id}"
        link_display = f"[Release]({html_url})" if html_url else "N/A"

        lines.append(f"| {display_name} | `{tag}` | {published} | {link_display} |")

    lines.append("")

    content = "\n".join(lines)

    with open(RELEASES_FILE, "w", encoding="utf-8") as f:
        f.write(content)

    return content


def main():
    """Main entry point."""
    print("Starting Coding Agent Monitor...")

    # Load configuration
    watchlist = load_watchlist()
    stored_versions = load_versions()

    # Fetch latest releases
    fetched_versions = {}
    for tool in watchlist:
        owner, repo = tool["owner"], tool["repo"]
        release = fetch_latest_release(owner, repo)
        if release:
            fetched_versions[tool["id"]] = release
            print(f"Fetched {tool['id']}: {release['tag_name']}")

    if not fetched_versions:
        print("Error: Failed to fetch any releases", file=sys.stderr)
        sys.exit(1)

    # Detect changes
    changes = detect_changes(watchlist, fetched_versions, stored_versions)
    first_run = is_first_run(stored_versions, watchlist)

    # Build and send appropriate message
    if first_run:
        message = build_initial_message(watchlist, fetched_versions)
        print("First run detected, sending initialization message")
    elif changes:
        print(f"Detected {len(changes)} new release(s)")
        messages = []
        for tool_id, old_tag, new_release in changes:
            tool = next(t for t in watchlist if t["id"] == tool_id)
            messages.append(build_alert_message(tool, old_tag, new_release))
        message = "\n\n".join(messages)
    else:
        message = build_status_message(watchlist, fetched_versions)
        print("No changes detected")

    # Send to Discord
    send_discord_message(message)

    # Update versions.json (only if changed or first run)
    new_versions = {}
    for tool in watchlist:
        tool_id = tool["id"]
        if tool_id in fetched_versions:
            release = fetched_versions[tool_id]
            new_versions[tool_id] = {
                "tag": release["tag_name"],
                "published_at": release["published_at"],
            }

    # Only save if versions changed or first run
    if first_run or new_versions != stored_versions:
        save_versions(new_versions)
        print("Updated versions.json")

    # Always update RELEASES.md
    update_markdown(watchlist, fetched_versions)
    print("Updated RELEASES.md")

    print("Monitor completed successfully")


if __name__ == "__main__":
    main()
