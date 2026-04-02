# AGENTS.md

Guidelines for AI agents working on this project.

> **Note:** Always update this file when making changes to the project structure, commands, or conventions.

## Project Overview

`cloner` is a minimal CLI tool for cloning git repositories to a structured workspace directory. It parses git URLs and clones them to `$CLONER_WORKSPACE/<path>` where path is derived from the URL (owner/repo or nested groups for GitLab).

## Tech Stack

- Python 3.11+
- No external runtime dependencies (stdlib only)
- `uv` for package management and tool installation
- `ruff` for linting and formatting
- `pre-commit` for git hooks

## Commands

```bash
# Run tests
uv run pytest

# Lint
uv run ruff check .

# Format
uv run ruff format .

# Install locally for testing
uv tool install . --force

# Run pre-commit on all files
uv run pre-commit run --all-files
```

## Code Style

- Line length: 88 characters
- Use ruff for linting and formatting
- No external dependencies in runtime code (keep it stdlib-only)

## Development Workflow

- **TDD**: Always use red/green TDD - write failing test first, then implement
- **README**: Update README.md when adding or changing features
- **Version bumps**: Update version in BOTH places:
  1. `cloner/__init__.py` (`__version__`)
  2. `pyproject.toml` (`version` field)

## Architecture

```
cloner/
├── __init__.py    # Version
├── cli.py         # Argument parsing, --init shell function output
└── core.py        # URL parsing, clone logic
tests/
├── test_core.py   # Unit tests for URL parsing
└── test_config.py # Tests for config mapping, git user config
```

### Key Functions

- `parse_git_url_info(url: str) -> tuple[str | None, str]`: Extracts hostname and path from git URL.
- `parse_git_url(url: str) -> Path`: Parses HTTPS/SSH URLs and returns the relative path for cloning (with hostname prefix for non-GitHub).
- `load_config() -> dict[str, str]`: Loads configuration from `~/.config/cloner.toml`.
- `resolve_url(url: str) -> tuple[Path, dict[str, str]]`: Resolves URL to `(target_dir, git_user_config)`. Handles prefix matching and git user config extraction.
- `configure_git_user(repo_path: Path, git_user: dict[str, str])`: Sets local `user.name`/`user.email`/`user.signingKey` in a repo.
- `get_workspace() -> Path`: Returns the workspace directory (from env or default `~/p`).
- `clone_or_cd(url: str) -> Path`: Clones repo or returns path if exists. Applies git user config if configured.

### Configuration Logic

1. Parse URL to get `hostname` and `path`.
2. Construct `full_path = f"{hostname}/{path}"` (or just `path` if no hostname).
3. Collect default git user from `[git]` section (optional `name`, `email`).
4. Find the longest key in `~/.config/cloner.toml` that is a prefix of `full_path`.
5. If matched:
   - If value is a string: Target = `value / (full_path - key)`
   - If value is a table: Target = `entry["path"] / (full_path - key)`, override git user with `git_name`/`git_email`/`git_signing_key` if present.
6. If no match:
   - Use default `$CLONER_WORKSPACE` logic.
7. After clone (or on cd to existing repo), apply git user config locally if any was resolved.

### Shell Integration

The `--init` flag outputs a shell function that:
1. Wraps the `clone` command
2. Captures the output directory
3. Changes to that directory

Users add `eval "$(clone --init)"` to their shell config.

## Important Notes

- GitHub repos: no hostname prefix (just owner/repo)
- Non-GitHub repos: include hostname prefix (e.g., codeberg.org/owner/repo)
- If repo exists locally (has `.git` dir), skip clone and just cd
- Support nested groups for GitLab (e.g., `group/subgroup/repo`)
- Support custom SSH ports for self-hosted Gitea
