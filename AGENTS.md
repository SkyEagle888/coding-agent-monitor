# AGENTS.md - Coding Agent Monitor

This file provides guidance for agentic coding agents operating in this repository.

## Project Overview

Python script that monitors GitHub release pages of AI coding CLI tools daily and sends Discord notifications when new versions are published. Runs on GitHub Actions.

## Build / Run Commands

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run the monitor
python monitor.py

# Run with environment variables
DISCORD_WEBHOOK_URL=<webhook_url> GH_TOKEN=<github_token> python monitor.py
```

### GitHub Actions (Production)
```bash
# The workflow runs on schedule (daily at 02:15 UTC)
# Trigger manually: Actions → Coding Agent Monitor → Run workflow
```

### Testing
- No test suite exists. Manual testing via:
  ```bash
  python monitor.py  # Verify it runs without errors
  ```

### Linting (Optional)
```bash
# Install pylint or ruff
pip install ruff

# Run linter
ruff check monitor.py
```

## Code Style Guidelines

### Imports
- Standard library first, then third-party, then local
- Group: stdlib → external → local
- Use absolute imports for project modules
- Example:
  ```python
  import json
  import os
  import sys
  from datetime import datetime
  from pathlib import Path

  import pytz
  import requests
  ```

### Formatting
- Line length: 100 characters max
- Indentation: 4 spaces
- Use f-strings for string formatting
- Use trailing commas in multi-line structures

### Types
- Python 3.10+ (type hints optional but recommended for new functions)
- Use `None` instead of `Null`
- Be explicit with return types for complex functions:
  ```python
  def fetch_latest_release(owner: str, repo: str) -> dict[str, Any]:
  ```

### Naming Conventions
- Functions/variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Classes (if any): `PascalCase`
- Private functions: prefix with `_`

### Error Handling
- Use specific exception types when possible
- Log errors to stderr: `print(..., file=sys.stderr)`
- Return error dicts instead of raising for expected failures
- Example:
  ```python
  try:
      response = requests.get(url, headers=headers, timeout=30)
      response.raise_for_status()
      return response.json()
  except requests.exceptions.RequestException as e:
      print(f"Error fetching {owner}/{repo}: {e}", file=sys.stderr)
      return {"error": str(e)}
  ```

### Docstrings
- Use Google-style or simple docstrings for public functions
- Keep brief (1-3 lines for simple functions)
- Example:
  ```python
  def load_watchlist():
      """Load the watchlist configuration."""
      with open(WATCHLIST_FILE, "r", encoding="utf-8") as f:
          return json.load(f)
  ```

### Constants
- Define at module level in UPPER_SCASE
- Group related constants
- Add brief comments for non-obvious values
- Example:
  ```python
  # API
  GITHUB_API_BASE = "https://api.github.com/repos"

  # Limits
  DISCORD_MAX_LENGTH = 2000
  RELEASE_NOTES_TRUNCATE = 800
  MAX_VERSION_HISTORY = 5
  ```

### File Operations
- Always use `encoding="utf-8"`
- Use `Path` from pathlib for file paths
- Context managers for file I/O
- Add trailing newline when writing JSON:
  ```python
  with open(VERSIONS_FILE, "w", encoding="utf-8") as f:
      json.dump(versions, f, indent=2)
      f.write("\n")
  ```

### Environment Variables
- Check with `.get()` to avoid KeyError
- Provide clear warning if missing
- Example:
  ```python
  webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
  if not webhook_url:
      print("Warning: DISCORD_WEBHOOK_URL not set, skipping...", file=sys.stderr)
      return
  ```

### GitHub Actions Integration
- Output JSON for workflow consumption via `/tmp/` files
- Use `id:` on steps to capture outputs
- Print status messages for debugging

## Project-Specific Conventions

### Version History Format
- Store up to MAX_VERSION_HISTORY (5) versions per tool
- Newest first (index 0 is latest)
- Full release notes stored in `body` field
- Automatic backward compatibility for old format

### JSON Data Files
- `watchlist.json`: Tool list to monitor
- `versions.json`: Persisted version history
- `RELEASES.md`: Auto-generated release table
- `CHANGELOG.md`: Auto-generated change log
- `.fetch_failures.json`: Failure tracking for issue creation

### Discord Messages
- Split long messages to stay under DISCORD_MAX_LENGTH (2000)
- Use emoji prefixes for visual organization
- Always include links to releases

### Timezone
- Use HKT (Asia/Hong_Kong) for display: `TZ_HKT = pytz.timezone("Asia/Hong_Kong")`
- ISO format for storage

## File Structure

```
coding-agent-monitor/
├── .github/workflows/monitor.yml  # GitHub Actions workflow
├── dashboard/                     # Static dashboard HTML
├── project-documents/             # Requirements & implementation docs
├── monitor.py                     # Main script
├── watchlist.json                # Tools to monitor
├── versions.json                 # Version history (auto-updated)
├── RELEASES.md                   # Release table (auto-updated)
├── CHANGELOG.md                  # Change log (auto-updated)
├── requirements.txt               # Python dependencies
└── README.md                     # Documentation
```

## Dependencies

- Python 3.10+
- `requests` - HTTP library
- `pytz` - Timezone handling

No other external dependencies.