# ✅ Implementation Plan — Coding Agent Monitor

> Task checklist for building and deploying the coding-agent-monitor from scratch.

---

## Phase 1 — Repository Setup

- [ ] **1.1** Create new GitHub repository `coding-agent-monitor` (private or public)
- [ ] **1.2** Initialise with `README.md`
- [ ] **1.3** Add `project-documents/REQUIREMENTS.md` and `project-documents/IMPLEMENTATION_PLAN.md`
- [ ] **1.4** Create `requirements.txt` with `requests` and `pytz`
- [ ] **1.5** Create `watchlist.json` with initial 4 tools:
  ```json
  [
    { "id": "gemini-cli",     "owner": "google-gemini",  "repo": "gemini-cli",     "emoji": "🟦" },
    { "id": "qwen-code",      "owner": "QwenLM",         "repo": "qwen-code",      "emoji": "🟧" },
    { "id": "opencode",       "owner": "anomalyco",      "repo": "opencode",       "emoji": "🟩" },
    { "id": "oh-my-opencode", "owner": "code-yeongyu",  "repo": "oh-my-opencode", "emoji": "🟥" }
  ]
  ```
- [ ] **1.6** Create empty `versions.json` (`{}`)

---

## Phase 2 — Python Monitor Script (`monitor.py`)

- [ ] **2.1** Load `watchlist.json` at startup
- [ ] **2.2** Implement `fetch_latest_release(owner, repo)` — calls GitHub API `/releases/latest`, returns `tag_name`, `name`, `published_at`, `html_url`, `body`; handles errors gracefully
- [ ] **2.3** Implement `load_versions()` — reads and parses `versions.json`; returns empty dict if file missing or empty
- [ ] **2.4** Implement `save_versions(versions)` — writes updated dict to `versions.json`
- [ ] **2.5** Implement `detect_changes(watchlist, fetched, stored)` — returns list of tools with new versions
- [ ] **2.6** Implement `update_markdown(watchlist, fetched)` — generates `RELEASES.md` (in repo root) with tool table + GMT+8 timestamp
- [ ] **2.7** Implement `send_discord_message(content)` — posts to webhook, splits at 1900-char boundary if needed
- [ ] **2.8** Implement `build_alert_message(tool, old_tag, new_release)` — formats the per-tool new release alert with emoji, version diff, date, URL, and truncated release notes
- [ ] **2.9** Implement `build_status_message(watchlist, fetched)` — formats the quiet daily status when no changes detected
- [ ] **2.10** Implement `build_initial_message(watchlist, fetched)` — formats the first-run setup confirmation
- [ ] **2.11** Wire up `main()` — orchestrate fetch → compare → notify → persist → update markdown
- [ ] **2.12** Ensure `GITHUB_TOKEN` env var is used as Bearer token in API requests if present (to avoid rate limits)

---

## Phase 3 — GitHub Actions Workflow (`.github/workflows/monitor.yml`)

- [ ] **3.1** Define workflow name: `Coding Agent Monitor`
- [ ] **3.2** Set cron schedule: `0 1 * * *` (daily 01:00 UTC / 09:00 HKT)
- [ ] **3.3** Add `workflow_dispatch` trigger for manual runs
- [ ] **3.4** Configure job on `ubuntu-latest` with `contents: write` permission
- [ ] **3.5** Add step: `actions/checkout@v4`
- [ ] **3.6** Add step: `actions/setup-python@v5` with Python `3.10`
- [ ] **3.7** Add step: install dependencies via `pip install -r requirements.txt`
- [ ] **3.8** Add step: run `monitor.py` with env vars `DISCORD_WEBHOOK_URL` and `GITHUB_TOKEN` injected from secrets
- [ ] **3.9** Add step: commit and push `versions.json` + `RELEASES.md` using `github-actions[bot]` with `[skip ci]` commit message

---

## Phase 4 — Secrets Configuration

- [ ] **4.1** Create Discord Webhook in target Discord server/channel
- [ ] **4.2** Add `DISCORD_WEBHOOK_URL` as a repository secret in GitHub Settings → Secrets → Actions
- [ ] **4.3** *(Optional)* Add `GH_TOKEN` (Personal Access Token with `public_repo` read scope) as a repository secret to raise API rate limit

---

## Phase 5 — Initial Data Bootstrap

- [ ] **5.1** Trigger workflow manually via Actions tab → **Run workflow**
- [ ] **5.2** Verify `versions.json` is committed with all 4 tools' current versions
- [ ] **5.3** Verify `RELEASES.md` is generated correctly in repo root
- [ ] **5.4** Verify Discord receives the initial setup message

---

## Phase 6 — Testing & Validation

- [ ] **6.1** Manually edit `versions.json` to set an older tag for one tool (e.g. `v0.29.0` for `gemini-cli`)
- [ ] **6.2** Trigger workflow manually — confirm Discord alert fires with the correct new version diff
- [ ] **6.3** Re-run with no changes — confirm quiet status message is sent
- [ ] **6.4** Confirm `[skip ci]` prevents looped workflow triggers
- [ ] **6.5** Confirm long release notes are split correctly when body exceeds 1900 characters

---

## Phase 7 — Documentation

- [ ] **7.1** Write `README.md` (repo root) with project overview, features, file structure, and fork setup instructions
- [ ] **7.2** Add GitHub Actions badge to `README.md`
- [ ] **7.3** Link to live `RELEASES.md` from `README.md`
- [ ] **7.4** *(Optional)* Add instructions for extending `watchlist.json` with additional tools

---

## Estimated Effort

| Phase | Tasks | Estimated Time |
|---|---|---|
| Phase 1 — Repo Setup | 6 tasks | 15 min |
| Phase 2 — Python Script | 12 tasks | 45 min |
| Phase 3 — GitHub Actions | 9 tasks | 20 min |
| Phase 4 — Secrets | 3 tasks | 5 min |
| Phase 5 — Bootstrap | 4 tasks | 10 min |
| Phase 6 — Testing | 5 tasks | 15 min |
| Phase 7 — Docs | 4 tasks | 15 min |
| **Total** | **43 tasks** | **~2 hours** |
