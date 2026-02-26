# 📋 Requirements — Coding Agent Monitor

> Monitors GitHub release pages of AI coding CLI tools daily and sends Discord notifications when a new version is published.

---

## 1. Monitored Tools

| Tool | GitHub Repo | API Endpoint |
|---|---|---|
| Gemini CLI | `google-gemini/gemini-cli` | `https://api.github.com/repos/google-gemini/gemini-cli/releases/latest` |
| Qwen Code CLI | `QwenLM/qwen-code` | `https://api.github.com/repos/QwenLM/qwen-code/releases/latest` |
| OpenCode | `anomalyco/opencode` | `https://api.github.com/repos/anomalyco/opencode/releases/latest` |
| Oh-My-OpenCode | `code-yeongyu/oh-my-opencode` | `https://api.github.com/repos/code-yeongyu/oh-my-opencode/releases/latest` |

---

## 2. Functional Requirements

### 2.1 Data Fetching
- The monitor MUST query the GitHub Releases API (`/releases/latest`) for each tool once per run.
- It MUST extract the following fields per tool:
  - `tag_name` — the version string (e.g. `v0.30.0`)
  - `name` — the release title
  - `published_at` — ISO 8601 timestamp
  - `html_url` — direct link to the release page
  - `body` — release notes (truncated to first 800 chars for Discord)
- It MUST handle HTTP errors (timeout, 4xx, 5xx) gracefully without crashing.
- It SHOULD use a `GITHUB_TOKEN` secret (optional) to raise the API rate limit from 60 to 5000 requests/hour.

### 2.2 State Management
- Detected versions MUST be persisted to `versions.json` in the repository.
- `versions.json` format:
  ```json
  {
    "gemini-cli":       { "tag": "v0.30.0", "published_at": "2026-02-25T03:05:56Z" },
    "qwen-code":        { "tag": "v0.10.6", "published_at": "2026-02-24T16:21:17Z" },
    "opencode":         { "tag": "v1.2.14", "published_at": "2026-02-25T14:56:11Z" },
    "oh-my-opencode":   { "tag": "v3.8.5",  "published_at": "2026-02-24T09:46:26Z" }
  }
  ```
- `versions.json` MUST only be committed when at least one version has changed.
- `RELEASES.md` MUST be regenerated on every run (with a fresh GMT+8 timestamp), regardless of whether versions changed.

### 2.3 Change Detection
- On each run, the script MUST compare fetched `tag_name` against the stored value per tool.
- A **new release** is detected when the fetched tag differs from the stored tag.
- First run (empty `versions.json`) is treated as **initial setup** — all tools are recorded but no "new release" alert is sent; an initialisation message is sent instead.

### 2.4 Discord Notifications
- The `DISCORD_WEBHOOK_URL` MUST be stored as a GitHub Actions secret.
- On **no changes**: send a quiet daily status message listing all tools and their current versions.
- On **new release(s) detected**: send an alert message per changed tool including:
  - Tool name + emoji
  - Old version → New version
  - Release date (GMT+8)
  - Direct link to release page
  - First 800 characters of release notes
- Messages exceeding Discord's 2000-character limit MUST be split into multiple sequential posts.
- On **initial run**: send a setup confirmation listing all tracked tools and their starting versions.

### 2.5 Human-Readable Summary
- `RELEASES.md` MUST be maintained in the repository root.
- It MUST display a table of all tools with: tool name, current version, release date, and a link to the release page.
- It MUST show a `Last updated` timestamp in GMT+8.

---

## 3. Non-Functional Requirements

| # | Requirement |
|---|---|
| NFR-1 | The monitor MUST run fully within GitHub Actions free tier (Ubuntu runner, Python 3.10+). |
| NFR-2 | Total runtime per run MUST complete within 2 minutes. |
| NFR-3 | No external paid services or databases — state is stored in the repository itself. |
| NFR-4 | All secrets (webhook URL, optional GitHub token) MUST be stored as GitHub Actions secrets, never hardcoded. |
| NFR-5 | The `[skip ci]` flag MUST be used on auto-commits to prevent workflow loops. |
| NFR-6 | The codebase MUST be easily forkable — all watched repos configurable via `watchlist.json`. |

---

## 4. Scheduling

- Runs **daily at 01:00 UTC** (09:00 HKT) via `cron: '0 1 * * *'`.
- Also triggerable manually via `workflow_dispatch`.

---

## 5. Repository Structure

```
coding-agent-monitor/
├── .github/
│   └── workflows/
│       └── monitor.yml           # GitHub Actions workflow
├── project-documents/
│   ├── REQUIREMENTS.md       # This file
│   └── IMPLEMENTATION_PLAN.md # Task checklist
├── monitor.py                # Main Python monitor script
├── watchlist.json            # Configurable list of repos to watch
├── versions.json             # Persisted latest versions (auto-updated)
├── RELEASES.md               # Human-readable release table (auto-updated)
├── requirements.txt          # Python dependencies
└── README.md                 # Project overview
```

---

## 6. Dependencies

```
requests
pytz
```

No other third-party libraries required. GitHub API is called via standard HTTP.
