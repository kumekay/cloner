# cloner

A minimal CLI tool for cloning git repositories into a structured workspace directory.

## Installation

```bash
uv tool install git+https://github.com/kumekay/cloner
```

Or from a local clone:

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
# GitHub shorthand (uses SSH)
clone kumekay/cloner
# → clones to ~/p/kumekay/cloner and cds there

# HTTPS
clone https://github.com/kumekay/kumekay.com.git
# → clones to ~/p/kumekay/kumekay.com and cds there

# SSH
clone git@github.com:kumekay/kumekay.com.git
# → clones to ~/p/kumekay/kumekay.com and cds there

# GitLab with nested groups
clone git@gitlab.com:org/team/project/repo.git
# → clones to ~/p/gitlab.com/org/team/project/repo and cds there

# Codeberg (non-GitHub hosts get hostname prefix)
clone https://codeberg.org/uzu/strudel.git
# → clones to ~/p/codeberg.org/uzu/strudel and cds there

# Self-hosted Gitea with custom port
clone ssh://git@gitea.example.com:2222/myorg/myrepo.git
# → clones to ~/p/gitea.example.com/myorg/myrepo and cds there
```

If the repository already exists locally, `clone` will just `cd` to it without re-cloning.

## Automatic Hook Installation

When cloning a repository (or cd-ing to an existing one), `clone` automatically detects and installs pre-commit hooks for the following hook managers:

| Manager | Detection | Install Command |
|---------|-----------|-----------------|
| [lefthook](https://github.com/evilmartians/lefthook) | `lefthook.yml` or `lefthook.toml` | `lefthook install` |
| [pre-commit](https://github.com/pre-commit/pre-commit) | `.pre-commit-config.yaml` | `pre-commit install` |
| [husky](https://github.com/typicode/husky) | `.husky/` directory | `npx husky` |

Hook installation is skipped when:
- Hooks are already installed (`.git/hooks/pre-commit` exists)
- The required tool binary is not found on `PATH`
- For husky: `core.hooksPath` is already configured

Hook installation failures are silently ignored to avoid blocking the clone/cd operation.

## Configuration

The tool can be configured via environment variables or a configuration file in `~/.config/cloner.toml`.

### Default Workspace

The default workspace directory (default: `~/p`) can be set in two ways:

1. **Environment Variable**:
   ```bash
   export CLONER_WORKSPACE=~/projects
   ```
2. **Configuration File** (`~/.config/cloner.toml`):
   ```toml
   workspace = "~/projects"
   ```

Priority: Environment variable > Config file > Default (`~/p`).

### Custom Destination Paths

You can configure specific destination paths for different hosts or organizations in `~/.config/cloner.toml`:

```toml
"github.com/myorg" = "~/work"
"github.com" = "~/projects"
"git.example.com" = "~/self-hosted"
```

With this config:
- `clone myorg/repo` → clones to `~/work/repo`
- `clone https://github.com/other/project.git` → clones to `~/projects/other/project`
- `clone ssh://git@git.example.com:2222/user/test.git` → clones to `~/self-hosted/user/test`

The tool uses the longest prefix match to determine the destination.

### Per-Repository Git User Config

You can configure `user.name` and `user.email` that get set locally in each cloned repository. This is useful when you use different identities for different hosts or organizations.

**Global default** (applies to all repos):

```toml
[git]
name = "Your Name"
email = "your@email.com"
signing_key = "ABCDEF1234567890"
```

**Per-prefix override** (use table syntax instead of a simple string value):

```toml
["github.com/work-org"]
path = "~/work"
git_name = "Work Name"
git_email = "work@corp.com"
git_signing_key = "WORKKEY123"
```

Per-prefix values override the global `[git]` defaults. The config sets `user.name`, `user.email`, and `user.signingKey` locally in each repo. It is applied both on fresh clones and when cd-ing into existing repos, so config changes take effect immediately.

## Supported URL Formats

| Format | Example |
|--------|---------|
| GitHub shorthand | `owner/repo` (uses SSH) |
| HTTPS | `https://github.com/owner/repo.git` |
| HTTPS (no .git) | `https://github.com/owner/repo` |
| SSH | `git@github.com:owner/repo.git` |
| SSH with port | `ssh://git@host:2222/owner/repo.git` |
| Nested groups | `git@gitlab.com:group/subgroup/repo.git` |

Works with GitHub, GitLab, Gitea (including self-hosted), and any other git hosting service.

## How It Works

1. Parses the git URL to extract hostname and path (owner/repo or nested groups)
2. Constructs the target directory: `$CLONER_WORKSPACE/<path>` for GitHub, `$CLONER_WORKSPACE/<hostname>/<path>` for others
3. If directory exists with `.git` inside → just return the path
4. Otherwise → `git clone <url> <target>` and return the path
5. Detects and installs pre-commit hooks if a supported hook manager is found
6. The shell function handles the `cd`

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
