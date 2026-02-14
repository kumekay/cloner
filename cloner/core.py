import os
import re
import subprocess
from pathlib import Path


def parse_git_url(url: str) -> Path:
    """
    Parse a git URL and return the relative path for cloning.

    Supported formats:
    - HTTPS: https://github.com/owner/repo.git
    - SSH: git@github.com:owner/repo.git
    - SSH with port: ssh://git@host:port/owner/repo.git
    - Nested groups (GitLab): git@gitlab.com:group/subgroup/repo.git
    """
    url = url.strip()

    if url.endswith("/"):
        url = url[:-1]

    if url.startswith(("https://", "http://")):
        path = url.split("/", 3)[-1]
    elif url.startswith("ssh://"):
        match = re.match(r"ssh://[^/]+/(.+)", url)
        if match:
            path = match.group(1)
        else:
            raise ValueError(f"Invalid SSH URL: {url}")
    elif ":" in url and "@" in url:
        path = url.split(":", 1)[1]
    else:
        raise ValueError(f"Unsupported URL format: {url}")

    if path.endswith(".git"):
        path = path[:-4]

    return Path(path)


def get_workspace() -> Path:
    return Path(os.environ.get("CLONER_WORKSPACE", "~/p")).expanduser()


def clone_or_cd(url: str) -> Path:
    """
    Clone a repository or return path if it already exists.
    Returns the path to the repository.
    """
    rel_path = parse_git_url(url)
    workspace = get_workspace()
    target_dir = workspace / rel_path

    if target_dir.exists() and (target_dir / ".git").exists():
        return target_dir

    target_dir.parent.mkdir(parents=True, exist_ok=True)

    result = subprocess.run(
        ["git", "clone", url, str(target_dir)],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(f"git clone failed: {result.stderr}")

    return target_dir
