# AGENTS.md

Guidelines for AI agents working on this project.

> **Note:** Always update this file when making changes to the project structure, commands, or conventions.

## Project Overview

`cloner` is a minimal CLI tool for cloning git repositories to a structured workspace directory. It parses git URLs and clones them to `$CLONER_WORKSPACE/<path>` where path is derived from the URL (owner/repo or nested groups for GitLab).

## Tech Stack

- Python 3.10+
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
└── test_core.py   # Unit tests for URL parsing
```

### Key Functions

- `parse_git_url(url: str) -> Path`: Parses HTTPS/SSH URLs and returns the relative path for cloning
- `get_workspace() -> Path`: Returns the workspace directory (from env or default `~/p`)
- `clone_or_cd(url: str) -> Path`: Clones repo or returns path if exists

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
