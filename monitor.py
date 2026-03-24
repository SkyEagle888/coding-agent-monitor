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
MAX_VERSION_HISTORY = 5  # Maximum number of previous versions to store per tool
SCRIPT_DIR = Path(__file__).parent.resolve()
VERSIONS_FILE = SCRIPT_DIR / "versions.json"
RELEASES_FILE = SCRIPT_DIR / "RELEASES.md"
CHANGELOG_FILE = SCRIPT_DIR / "CHANGELOG.md"
FAILURES_FILE = SCRIPT_DIR / ".fetch_failures.json"
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
    or error dict on failure.
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
        return {"error": str(e)}


def load_versions():
    """
    Load persisted versions from versions.json.
    
    Handles backward compatibility: converts old format (single version per tool)
    to new format (version history list with up to MAX_VERSION_HISTORY entries).
    
    Returns tuple of (versions_dict, needs_save) where:
    - versions_dict: The loaded/converted versions data
    - needs_save: True if old format was converted and should be saved
    
    New format:
    {
        "tool_id": {
            "versions": [
                {"tag": "v1.0.0", "name": "...", "published_at": "...", "body": "..."},
                ...
            ]
        }
    }
    """
    if not VERSIONS_FILE.exists():
        return {}, False

    try:
        with open(VERSIONS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}, False

    # Convert old format to new format for backward compatibility
    converted = {}
    needs_save = False
    
    for tool_id, tool_data in data.items():
        if isinstance(tool_data, dict) and "versions" in tool_data:
            # Already in new format
            converted[tool_id] = tool_data
        elif isinstance(tool_data, dict) and "tag" in tool_data:
            # Old format: convert to new format with single version in history
            converted[tool_id] = {
                "versions": [
                    {
                        "tag": tool_data.get("tag", "unknown"),
                        "name": tool_data.get("name", "unknown"),
                        "published_at": tool_data.get("published_at", ""),
                        "body": tool_data.get("body", ""),  # May be empty in old format
                    }
                ]
            }
            needs_save = True  # Mark that conversion happened
        else:
            # Unknown format, skip
            print(f"Warning: Skipping unknown format for {tool_id}", file=sys.stderr)

    return converted, needs_save


def save_versions(versions):
    """Save versions to versions.json."""
    with open(VERSIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(versions, f, indent=2)
        f.write("\n")


def load_fetch_failures():
    """Load fetch failure tracking data."""
    if not FAILURES_FILE.exists():
        return {}

    try:
        with open(FAILURES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def save_fetch_failures(failures):
    """Save fetch failure tracking data."""
    with open(FAILURES_FILE, "w", encoding="utf-8") as f:
        json.dump(failures, f, indent=2)
        f.write("\n")


def append_changelog_entry(tool_id, old_tag, new_tag, date_str):
    """Append a new entry to CHANGELOG.md."""
    today = datetime.now(TZ_HKT).strftime("%Y-%m-%d") if not date_str else date_str[:10]

    # Create file with header if it doesn't exist
    if not CHANGELOG_FILE.exists():
        with open(CHANGELOG_FILE, "w", encoding="utf-8") as f:
            f.write("# 📝 Version History\n\n")
            f.write("| Date | Tool | Change | Details |\n")
            f.write("|------|------|--------|--------|\n")

    # Append new entry
    with open(CHANGELOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"| {today} | {tool_id} | `{old_tag}` → `{new_tag}` | [Release](https://github.com/search?q={tool_id}+releases) |\n")


def detect_changes(watchlist, fetched_versions, stored_versions):
    """
    Compare fetched versions against stored versions.

    Returns tuple of (changes, fetch_failures) where:
    - changes: list of (tool_id, old_tag, new_release_data) tuples
    - fetch_failures: list of tool_ids that failed to fetch
    
    Uses the most recent version from the version history for comparison.
    """
    changes = []
    fetch_failures = []

    for tool in watchlist:
        tool_id = tool["id"]
        if tool_id not in fetched_versions:
            continue

        fetched = fetched_versions[tool_id]

        # Check for fetch error
        if "error" in fetched:
            fetch_failures.append(tool_id)
            continue

        stored = stored_versions.get(tool_id, {})
        
        # Get the most recent version from history for comparison
        stored_version_list = stored.get("versions", [])
        old_tag = stored_version_list[0]["tag"] if stored_version_list else None
        
        new_tag = fetched.get("tag_name")

        # Skip if no change
        if old_tag == new_tag:
            continue

        # First run: record but don't alert
        if old_tag is None:
            continue

        changes.append((tool_id, old_tag, fetched))

    return changes, fetch_failures


def is_first_run(stored_versions, watchlist):
    """Check if this is the first run (no versions stored)."""
    if not stored_versions:
        return True

    # Check if all watched tools have stored versions with at least one entry
    for tool in watchlist:
        tool_id = tool["id"]
        if tool_id not in stored_versions:
            return True
        stored = stored_versions.get(tool_id, {})
        if not stored.get("versions"):
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


def build_status_message(watchlist, fetched_versions, fetch_failures):
    """Build quiet daily status message when no changes detected."""
    lines = ["📊 **Daily Status Report**", ""]

    for tool in watchlist:
        tool_id = tool["id"]
        emoji = tool.get("emoji", "📦")
        fetched = fetched_versions.get(tool_id, {})

        if "error" in fetched:
            lines.append(f"{emoji} **{tool_id}**: ⚠️ Fetch failed - {fetched.get('error', 'Unknown error')}")
        else:
            tag = fetched.get("tag_name", "unknown")
            published = format_timestamp_gmt8(fetched.get("published_at", ""))
            lines.append(f"{emoji} **{tool_id}**: `{tag}` ({published})")

    # Add fetch failure warning section
    if fetch_failures:
        lines.append("")
        lines.append("⚠️ **Fetch Failures:**")
        for tool_id in fetch_failures:
            lines.append(f"- {tool_id}: Unable to fetch release data")

    lines.append("")
    lines.append("No new releases detected today.")

    return "\n".join(lines)


def build_initial_message(watchlist, fetched_versions, fetch_failures):
    """Build first-run setup confirmation message."""
    lines = ["✅ **Monitor Initialized**", ""]
    lines.append("Now tracking the following tools:")
    lines.append("")

    for tool in watchlist:
        tool_id = tool["id"]
        emoji = tool.get("emoji", "📦")
        fetched = fetched_versions.get(tool_id, {})

        if "error" in fetched:
            lines.append(f"{emoji} **{tool_id}**: ⚠️ Fetch failed - {fetched.get('error', 'Unknown error')}")
        else:
            tag = fetched.get("tag_name", "unknown")
            published = format_timestamp_gmt8(fetched.get("published_at", ""))
            lines.append(f"{emoji} **{tool_id}**: `{tag}` (since {published})")

    # Add fetch failure warning section
    if fetch_failures:
        lines.append("")
        lines.append("⚠️ **Fetch Failures:**")
        for tool_id in fetch_failures:
            lines.append(f"- {tool_id}: Unable to fetch release data")

    lines.append("")
    lines.append("You will be notified when new releases are published.")

    return "\n".join(lines)


def build_changes_message(watchlist, changes, fetch_failures):
    """Build Discord message for detected changes."""
    messages = []

    for tool_id, old_tag, new_release in changes:
        tool = next(t for t in watchlist if t["id"] == tool_id)
        messages.append(build_alert_message(tool, old_tag, new_release))

    base_message = "\n\n".join(messages)

    # Append fetch failure warnings if any
    if fetch_failures:
        failure_lines = ["", "⚠️ **Fetch Failures:**"]
        for tool_id in fetch_failures:
            failure_lines.append(f"- {tool_id}: Unable to fetch release data")
        base_message += "\n\n" + "\n".join(failure_lines)

    return base_message


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


def update_markdown(watchlist, fetched_versions, workflow_status="unknown"):
    """Generate RELEASES.md with current versions table and status badge."""
    now_hkt = datetime.now(TZ_HKT).strftime("%Y-%m-%d %H:%M:%S HKT")

    # Build status badge
    if workflow_status == "success":
        badge = "![Workflow Status](https://github.com/SkyEagle888/coding-agent-monitor/actions/workflows/monitor.yml/badge.svg?branch=main&event=schedule)"
    else:
        badge = "![Workflow Status](https://github.com/SkyEagle888/coding-agent-monitor/actions/workflows/monitor.yml/badge.svg?branch=main)"

    lines = [
        "# 📦 AI Coding Tools Release Tracker",
        "",
        badge,
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

        if "error" in fetched:
            display_name = f"{emoji} {tool_id}"
            lines.append(f"| {display_name} | ⚠️ Error | - | - |")
        else:
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


def get_issue_title(tool_id, error_msg):
    """Generate issue title for fetch failure."""
    return f"⚠️ Fetch failure: {tool_id}"


def output_issue_data(fetch_failures, fetched_versions, failure_history):
    """Output data for GitHub issue creation via workflow."""
    issues_to_create = []

    for tool_id in fetch_failures:
        # Get consecutive failure count
        failure_count = failure_history.get(tool_id, {}).get("count", 1)

        # Only create issue if 2+ consecutive failures
        if failure_count >= 2:
            error_msg = fetched_versions.get(tool_id, {}).get("error", "Unknown error")
            issues_to_create.append({
                "tool_id": tool_id,
                "title": get_issue_title(tool_id, error_msg),
                "body": f"""## Fetch Failure Alert

**Tool:** {tool_id}
**Consecutive Failures:** {failure_count}
**Error:** {error_msg}

### Suggested Actions
- Check if the repository has been renamed or moved
- Verify the repository still exists
- Update `watchlist.json` if the owner/repo has changed

---
*This issue was auto-created by the Coding Agent Monitor workflow.*
""",
                "labels": ["bug", "fetch-failure"],
            })

    # Output as JSON for workflow to consume
    if issues_to_create:
        with open("/tmp/issues_to_create.json", "w") as f:
            json.dump(issues_to_create, f)
        print(f"ISSUES_TO_CREATE={json.dumps(issues_to_create)}")

    return issues_to_create


def update_failure_history(fetch_failures, all_failures_cleared):
    """Update failure tracking history."""
    failure_history = load_fetch_failures()
    now = datetime.now(TZ_HKT).isoformat()

    for tool_id in fetch_failures:
        if tool_id not in failure_history:
            failure_history[tool_id] = {"count": 1, "first_failure": now, "last_error": ""}
        else:
            failure_history[tool_id]["count"] += 1
            failure_history[tool_id]["last_error"] = ""

    # Clear failures for tools that succeeded
    for tool_id in list(failure_history.keys()):
        if tool_id not in fetch_failures:
            del failure_history[tool_id]

    save_fetch_failures(failure_history)
    return failure_history


def update_version_history(stored_versions, tool_id, new_release):
    """
    Update the version history for a tool with a new release.
    
    Maintains a maximum of MAX_VERSION_HISTORY versions, with the newest first.
    When a new version is detected, it's prepended to the list and the oldest
    is removed if the list exceeds the maximum.
    
    Args:
        stored_versions: The current versions dict (modified in place)
        tool_id: The tool identifier
        new_release: The new release data from GitHub API
    """
    if tool_id not in stored_versions:
        stored_versions[tool_id] = {"versions": []}
    
    version_list = stored_versions[tool_id]["versions"]
    
    # Create new version entry with all required fields
    new_version = {
        "tag": new_release["tag_name"],
        "name": new_release["name"],
        "published_at": new_release["published_at"],
        "body": new_release.get("body", ""),  # Store full release notes
    }
    
    # Check if this version already exists (avoid duplicates)
    existing_tags = [v["tag"] for v in version_list]
    if new_version["tag"] in existing_tags:
        # Version already in history, move to front if not already there
        if version_list and version_list[0]["tag"] != new_version["tag"]:
            # Find and remove the existing version with the same tag
            version_list[:] = [v for v in version_list if v["tag"] != new_version["tag"]]
            version_list.insert(0, new_version)
        return
    
    # Prepend new version (newest first)
    version_list.insert(0, new_version)
    
    # Trim to maximum history size
    while len(version_list) > MAX_VERSION_HISTORY:
        version_list.pop()


def main():
    """Main entry point."""
    print("Starting Coding Agent Monitor...")

    # Load configuration
    watchlist = load_watchlist()
    stored_versions, format_converted = load_versions()

    # Fetch latest releases
    fetched_versions = {}
    for tool in watchlist:
        owner, repo = tool["owner"], tool["repo"]
        release = fetch_latest_release(owner, repo)
        fetched_versions[tool["id"]] = release

        if release and "error" not in release:
            print(f"Fetched {tool['id']}: {release['tag_name']}")
        elif release and "error" in release:
            print(f"Failed to fetch {tool['id']}: {release['error']}", file=sys.stderr)

    # Check if all fetches failed
    successful_fetches = {k: v for k, v in fetched_versions.items() if v and "error" not in v}
    if not successful_fetches:
        print("Error: Failed to fetch any releases", file=sys.stderr)
        sys.exit(1)

    # Detect changes and fetch failures
    changes, fetch_failures = detect_changes(watchlist, fetched_versions, stored_versions)
    first_run = is_first_run(stored_versions, watchlist)

    # Update failure history and get issues to create
    failure_history = update_failure_history(fetch_failures, not fetch_failures)
    issues_to_create = output_issue_data(fetch_failures, fetched_versions, failure_history)

    # Build and send appropriate message
    if first_run:
        message = build_initial_message(watchlist, fetched_versions, fetch_failures)
        print("First run detected, sending initialization message")
    elif changes:
        print(f"Detected {len(changes)} new release(s)")
        message = build_changes_message(watchlist, changes, fetch_failures)
    else:
        message = build_status_message(watchlist, fetched_versions, fetch_failures)
        print("No changes detected")

    # Send to Discord
    send_discord_message(message)

    # Update versions.json with version history
    # Save if: first run, new versions detected, or format conversion needed
    versions_changed = first_run or bool(changes)
    needs_save = versions_changed or format_converted

    if needs_save:
        # Update version history for each tool with successful fetch
        if versions_changed:
            for tool in watchlist:
                tool_id = tool["id"]
                if tool_id in fetched_versions:
                    release = fetched_versions[tool_id]
                    if release and "error" not in release:
                        update_version_history(stored_versions, tool_id, release)

        save_versions(stored_versions)
        print("Updated versions.json")

        # Update changelog for each changed tool
        if changes:
            for tool_id, old_tag, new_release in changes:
                new_tag = new_release.get("tag_name")
                append_changelog_entry(tool_id, old_tag, new_tag, new_release.get("published_at", ""))
            print("Updated CHANGELOG.md")

    # Always update RELEASES.md
    update_markdown(watchlist, fetched_versions)
    print("Updated RELEASES.md")

    print("Monitor completed successfully")


if __name__ == "__main__":
    main()
