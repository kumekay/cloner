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


def load_config() -> dict[str, str]:
    config_home = os.environ.get("XDG_CONFIG_HOME")
    if config_home:
        config_path = Path(config_home) / "cloner.toml"
    else:
        config_path = Path.home() / ".config" / "cloner.toml"

    if not config_path.exists():
        return {}

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


def get_target_dir(url: str) -> Path:
    hostname, path = parse_git_url_info(url)
    config = load_config()

    full_path = f"{hostname}/{path}" if hostname else path

    # Try to find longest prefix match in config (excluding special keys)
    prefixes = {k: v for k, v in config.items() if k != "workspace"}
    for key in sorted(prefixes.keys(), key=len, reverse=True):
        if full_path.startswith(key):
            base = Path(prefixes[key]).expanduser()
            relative = full_path[len(key) :].lstrip("/")
            return base / relative

    # Default logic
    workspace = get_workspace()
    rel_path = parse_git_url(url)
    return workspace / rel_path


def clone_or_cd(url: str) -> Path:
    """
    Clone a repository or return path if it already exists.
    Returns the path to the repository.
    """
    url = normalize_url(url)
    target_dir = get_target_dir(url)

    if target_dir.exists() and (target_dir / ".git").exists():
        return target_dir

    target_dir.parent.mkdir(parents=True, exist_ok=True)

    result = subprocess.run(["git", "clone", url, str(target_dir)])

    if result.returncode != 0:
        raise RuntimeError("git clone failed")

    return target_dir
