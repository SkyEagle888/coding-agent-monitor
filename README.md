# coding-agent-monitor

GitHub Actions monitor that tracks new releases of AI coding CLI tools (Gemini CLI, Qwen Code, OpenCode, Oh-My-OpenCode) and sends Discord notifications on updates.

[![Workflow Status](https://github.com/SkyEagle888/coding-agent-monitor/actions/workflows/monitor.yml/badge.svg)](https://github.com/SkyEagle888/coding-agent-monitor/actions/workflows/monitor.yml)

## Features

- 🔄 **Automated Monitoring** - Checks for new releases daily at 01:00 UTC (09:00 HKT)
- 📬 **Discord Notifications** - Instant alerts when new versions are published
- 📊 **Release Tracker** - Maintains a human-readable `RELEASES.md` with current versions
- 📜 **Version History** - Stores up to 5 previous versions per tool with full release notes
- 🔧 **Configurable** - Easy to extend with additional tools via `watchlist.json`
- 💰 **Free Tier Friendly** - Runs entirely on GitHub Actions free tier

## Monitored Tools

| Tool | GitHub Repo |
|------|-------------|
| Gemini CLI | [google-gemini/gemini-cli](https://github.com/google-gemini/gemini-cli) |
| Qwen Code CLI | [QwenLM/qwen-code](https://github.com/QwenLM/qwen-code) |
| OpenCode | [anomalyco/opencode](https://github.com/anomalyco/opencode) |
| Oh-My-OpenCode | [code-yeongyu/oh-my-opencode](https://github.com/code-yeongyu/oh-my-opencode) |

## File Structure

```
coding-agent-monitor/
├── .github/
│   └── workflows/
│       └── monitor.yml           # GitHub Actions workflow
├── project-documents/
│   ├── REQUIREMENTS.md           # Detailed requirements
│   └── IMPLEMENTATION_PLAN.md    # Implementation checklist
├── monitor.py                    # Main Python monitor script
├── watchlist.json                # Configurable list of repos to watch
├── versions.json                 # Persisted version history (auto-updated, max 5 versions per tool)
├── RELEASES.md                   # Human-readable release table (auto-updated)
├── CHANGELOG.md                  # Version change history log (auto-updated)
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

## Setup Instructions

### 1. Fork/Clone the Repository

```bash
git clone https://github.com/SkyEagle888/coding-agent-monitor.git
cd coding-agent-monitor
```

### 2. Configure Discord Webhook

1. In your Discord server, go to **Server Settings** → **Integrations** → **Webhooks**
2. Click **New Webhook** and select the channel for notifications
3. Copy the **Webhook URL**

### 3. Add GitHub Secrets

Go to your repository's **Settings** → **Secrets and variables** → **Actions** and add:

| Secret Name | Description | Required |
|-------------|-------------|----------|
| `DISCORD_WEBHOOK_URL` | Your Discord webhook URL | ✅ Yes |
| `GH_TOKEN` | GitHub Personal Access Token with `public_repo` read scope | ❌ Optional (recommended for rate limits) |

> **Security Note:** The Discord webhook URL is stored as a GitHub secret and is never hardcoded in the repository.

### 4. Enable the Workflow

1. Go to the **Actions** tab in your repository
2. Click on **Coding Agent Monitor** workflow
3. Click **Enable workflow**
4. Trigger the first run manually with **Run workflow**

### 5. Verify Initial Run

After the first run:
- Check `versions.json` is populated with current versions
- Check `RELEASES.md` is generated
- Verify Discord receives the initialization message

## Customization

### Adding New Tools

Edit `watchlist.json` to add more tools:

```json
[
  { "id": "gemini-cli", "owner": "google-gemini", "repo": "gemini-cli", "emoji": "🟦" },
  { "id": "your-tool", "owner": "owner-name", "repo": "repo-name", "emoji": "🚀" }
]
```

### Changing Schedule

Edit `.github/workflows/monitor.yml` and modify the cron expression:

```yaml
schedule:
  - cron: '0 1 * * *'  # Daily at 01:00 UTC
```

Use [crontab.guru](https://crontab.guru/) to generate cron expressions.

## Data Formats

### versions.json

The `versions.json` file stores version history for each tracked tool. It maintains up to 5 previous versions with full release notes:

```json
{
  "tool-id": {
    "versions": [
      {
        "tag": "v1.2.0",
        "name": "Release v1.2.0",
        "published_at": "2026-03-20T12:00:00Z",
        "body": "Full release notes from GitHub..."
      },
      {
        "tag": "v1.1.0",
        "name": "Release v1.1.0",
        "published_at": "2026-03-15T10:00:00Z",
        "body": "Previous release notes..."
      }
    ]
  }
}
```

**Notes:**
- Versions are ordered newest first (index 0 is the latest)
- Maximum 5 versions are retained per tool
- When a new version is detected, the oldest is automatically removed
- The `body` field contains the full release notes from GitHub
- Backward compatible: old format (single version per tool) is automatically converted on first run

## Dependencies

- Python 3.10+
- [requests](https://pypi.org/project/requests/) - HTTP library
- [pytz](https://pypi.org/project/pytz/) - Timezone handling

## License

MIT
