# cloner

A minimal CLI tool for cloning git repositories into a structured workspace directory.

## Installation

```bash
uv tool install .
```

Or from the directory:

```bash
uv tool install /path/to/cloner
```

## Shell Setup

Add to your `.zshrc` or `.bashrc`:

```bash
eval "$(clone --init)"
```

Then reload your shell or run `source ~/.zshrc`.

## Usage

```bash
clone <git-url>
```

The tool clones the repository into your workspace and automatically changes to that directory.

### Examples

```bash
# HTTPS
clone https://github.com/kumekay/kumekay.com.git
# → clones to ~/p/kumekay/kumekay.com and cds there

# SSH
clone git@github.com:kumekay/kumekay.com.git
# → clones to ~/p/kumekay/kumekay.com and cds there

# GitLab with nested groups
clone git@gitlab.com:org/team/project/repo.git
# → clones to ~/p/org/team/project/repo and cds there

# Self-hosted Gitea with custom port
clone ssh://git@gitea.example.com:2222/myorg/myrepo.git
# → clones to ~/p/myorg/myrepo and cds there
```

If the repository already exists locally, `clone` will just `cd` to it without re-cloning.

## Configuration

Set the `CLONER_WORKSPACE` environment variable to customize the base directory:

```bash
export CLONER_WORKSPACE=~/projects
```

Default: `~/p`

## Supported URL Formats

| Format | Example |
|--------|---------|
| HTTPS | `https://github.com/owner/repo.git` |
| HTTPS (no .git) | `https://github.com/owner/repo` |
| SSH | `git@github.com:owner/repo.git` |
| SSH with port | `ssh://git@host:2222/owner/repo.git` |
| Nested groups | `git@gitlab.com:group/subgroup/repo.git` |

Works with GitHub, GitLab, Gitea (including self-hosted), and any other git hosting service.

## How It Works

1. Parses the git URL to extract the path (owner/repo or nested groups)
2. Constructs the target directory: `$CLONER_WORKSPACE/<path>`
3. If directory exists with `.git` inside → just return the path
4. Otherwise → `git clone <url> <target>` and return the path
5. The shell function handles the `cd`

## Development

```bash
# Install dev dependencies
uv sync --group dev

# Run tests
uv run pytest

# Run linter
uv run ruff check .

# Format code
uv run ruff format .
```
