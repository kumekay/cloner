import os
import re
import subprocess
import tomllib
from pathlib import Path


def normalize_url(url: str) -> str:
    """
    Normalize URL, converting GitHub shorthand to SSH URL.

    GitHub shorthand: org/repo -> git@github.com:org/repo.git
    """
    url = url.strip()

    if "/" in url and not url.startswith(("https://", "http://", "ssh://", "git@")):
        return f"git@github.com:{url}.git"

    return url


def parse_git_url_info(url: str) -> tuple[str | None, str]:
    """
    Parse a git URL and return (hostname, path).
    """
    url = url.strip()

    if url.endswith("/"):
        url = url[:-1]

    hostname = None
    if url.startswith(("https://", "http://")):
        parts = url.split("/", 3)
        hostname = parts[2]
        path = parts[3] if len(parts) > 3 else ""
    elif url.startswith("ssh://"):
        match = re.match(r"ssh://([^@]+@)?([^/:]+)(:\d+)?/(.+)", url)
        if match:
            hostname = match.group(2)
            path = match.group(4)
        else:
            raise ValueError(f"Invalid SSH URL: {url}")
    elif ":" in url and "@" in url:
        hostname = url.split("@", 1)[1].split(":")[0]
        path = url.split(":", 1)[1]
    else:
        raise ValueError(f"Unsupported URL format: {url}")

    if path.endswith(".git"):
        path = path[:-4]

    return hostname, path


def parse_git_url(url: str) -> Path:
    """
    Parse a git URL and return the relative path for cloning.

    Supported formats:
    - HTTPS: https://github.com/owner/repo.git
    - SSH: git@github.com:owner/repo.git
    - SSH with port: ssh://git@host:port/owner/repo.git
    - Nested groups (GitLab): git@gitlab.com:group/subgroup/repo.git

    Non-GitHub hosts get prefixed with hostname, e.g. codeberg.org/uzu/strudel
    """
    hostname, path = parse_git_url_info(url)

    if hostname and hostname != "github.com":
        path = f"{hostname}/{path}"

    return Path(path)


DEFAULT_CONFIG = """\
workspace = "~/p"

# Default git user for all repos (optional):
# [git]
# name = "Your Name"
# email = "your@email.com"
# signing_key = "ABCDEF1234567890"

# Custom destination paths (examples):
# "github.com/myorg" = "~/work"
# "codeberg.org" = "~/projects/codeberg"

# Per-prefix git user config (use table syntax):
# ["github.com/work-org"]
# path = "~/work"
# git_name = "Work Name"
# git_email = "work@email.com"
# git_signing_key = "ABCDEF1234567890"
"""


def load_config() -> dict[str, str]:
    config_home = os.environ.get("XDG_CONFIG_HOME")
    if config_home:
        config_path = Path(config_home) / "cloner.toml"
    else:
        config_path = Path.home() / ".config" / "cloner.toml"

    if not config_path.exists():
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(DEFAULT_CONFIG)

    with open(config_path, "rb") as f:
        return tomllib.load(f)


def get_workspace() -> Path:
    workspace = os.environ.get("CLONER_WORKSPACE")
    if workspace:
        return Path(workspace).expanduser()

    config = load_config()
    if "workspace" in config:
        return Path(config["workspace"]).expanduser()

    return Path("~/p").expanduser()


def resolve_url(url: str) -> tuple[Path, dict[str, str]]:
    """
    Resolve a git URL to (target_dir, git_user_config).

    git_user_config may contain "name", "email", and/or "signingKey" keys,
    matching git config keys under [user].
    """
    hostname, path = parse_git_url_info(url)
    config = load_config()

    full_path = f"{hostname}/{path}" if hostname else path

    # Default git user config from [git] section
    # Maps config file keys to git config keys (user.name, user.email, user.signingKey)
    git_user: dict[str, str] = {}
    git_section = config.get("git", {})
    if isinstance(git_section, dict):
        for key in ("name", "email"):
            if key in git_section:
                git_user[key] = git_section[key]
        if "signing_key" in git_section:
            git_user["signingKey"] = git_section["signing_key"]

    # Try to find longest prefix match in config (excluding special keys)
    special_keys = {"workspace", "git"}
    prefixes = {k: v for k, v in config.items() if k not in special_keys}
    for key in sorted(prefixes.keys(), key=len, reverse=True):
        if full_path.startswith(key):
            entry = prefixes[key]
            if isinstance(entry, str):
                base = Path(entry).expanduser()
            else:
                base = Path(entry["path"]).expanduser()
                for git_key in ("name", "email"):
                    if f"git_{git_key}" in entry:
                        git_user[git_key] = entry[f"git_{git_key}"]
                if "git_signing_key" in entry:
                    git_user["signingKey"] = entry["git_signing_key"]
            relative = full_path[len(key) :].lstrip("/")
            return base / relative, git_user

    # Default logic
    workspace = get_workspace()
    rel_path = parse_git_url(url)
    return workspace / rel_path, git_user


def configure_git_user(repo_path: Path, git_user: dict[str, str]) -> None:
    """Set local git user.name, user.email, and user.signingKey in the repo."""
    for key, value in git_user.items():
        subprocess.run(
            ["git", "-C", str(repo_path), "config", f"user.{key}", value],
            check=True,
        )


def clone_or_cd(url: str) -> Path:
    """
    Clone a repository or return path if it already exists.
    Returns the path to the repository.
    """
    url = normalize_url(url)
    target_dir, git_user = resolve_url(url)

    if target_dir.exists() and (target_dir / ".git").exists():
        if git_user:
            configure_git_user(target_dir, git_user)
        return target_dir

    target_dir.parent.mkdir(parents=True, exist_ok=True)

    result = subprocess.run(["git", "clone", url, str(target_dir)])

    if result.returncode != 0:
        raise RuntimeError("git clone failed")

    if git_user:
        configure_git_user(target_dir, git_user)

    return target_dir
