from pathlib import Path

import pytest

from cloner.core import clone_or_cd


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Ensure tests are isolated from the user's environment."""
    monkeypatch.delenv("CLONER_WORKSPACE", raising=False)
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)


@pytest.fixture
def mock_subprocess(monkeypatch):
    """Mock subprocess.run to simulate git clone and capture git config calls."""
    import subprocess

    class MockResult:
        returncode = 0

    git_config_calls = []

    def mock_run(args, **kwargs):
        if args[:2] == ["git", "clone"]:
            path = Path(args[3])
            (path / ".git").mkdir(parents=True)
        elif args[:2] == ["git", "-C"]:
            git_config_calls.append(args)
        return MockResult()

    monkeypatch.setattr(subprocess, "run", mock_run)
    return git_config_calls


def test_config_mapping_host_and_user(monkeypatch, tmp_path, mock_subprocess):
    # Setup workspace
    workspace = tmp_path / "p"
    workspace.mkdir()
    monkeypatch.setenv("CLONER_WORKSPACE", str(workspace))

    # Setup custom destination
    custom_dest = tmp_path / "custom"
    custom_dest.mkdir()

    # Mock config
    config_content = f'"github.com/myorg" = "{str(custom_dest)}"\n'

    config_dir = tmp_path / ".config"
    config_dir.mkdir()
    config_file = config_dir / "cloner.toml"
    config_file.write_text(config_content)

    # Mock Path.home() to point to tmp_path
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Test mapping for org
    url = "git@github.com:myorg/repo.git"
    target = clone_or_cd(url)

    assert target == custom_dest / "repo"
    assert target.exists()


def test_config_mapping_host_only(monkeypatch, tmp_path, mock_subprocess):
    workspace = tmp_path / "p"
    workspace.mkdir()
    monkeypatch.setenv("CLONER_WORKSPACE", str(workspace))

    custom_dest = tmp_path / "work"
    custom_dest.mkdir()

    config_content = f'"gitlab.com" = "{str(custom_dest)}"\n'

    config_dir = tmp_path / ".config"
    config_dir.mkdir()
    config_file = config_dir / "cloner.toml"
    config_file.write_text(config_content)

    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Test host-only mapping
    url = "https://gitlab.com/company/project.git"
    target = clone_or_cd(url)

    assert target == custom_dest / "company" / "project"


def test_config_mapping_self_hosted(monkeypatch, tmp_path, mock_subprocess):
    workspace = tmp_path / "p"
    workspace.mkdir()
    monkeypatch.setenv("CLONER_WORKSPACE", str(workspace))

    custom_dest = tmp_path / "gitea"
    custom_dest.mkdir(parents=True)

    config_content = f'"git.example.com" = "{str(custom_dest)}"\n'

    config_dir = tmp_path / ".config"
    config_dir.mkdir()
    config_file = config_dir / "cloner.toml"
    config_file.write_text(config_content)

    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Test self-hosted example
    url = "ssh://git@git.example.com:2222/user/repo.git"
    target = clone_or_cd(url)

    assert target == custom_dest / "user" / "repo"


def test_config_workspace(monkeypatch, tmp_path, mock_subprocess):
    # Setup custom workspace in config
    custom_workspace = tmp_path / "custom_p"
    custom_workspace.mkdir()

    config_content = f'workspace = "{str(custom_workspace)}"\n'

    config_dir = tmp_path / ".config"
    config_dir.mkdir()
    config_file = config_dir / "cloner.toml"
    config_file.write_text(config_content)

    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Test that it uses the workspace from config
    url = "git@github.com:org/repo.git"
    target = clone_or_cd(url)

    assert target == custom_workspace / "org" / "repo"


def test_config_xdg_home(monkeypatch, tmp_path, mock_subprocess):
    # Setup custom XDG_CONFIG_HOME
    xdg_home = tmp_path / "custom_config"
    xdg_home.mkdir()
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg_home))

    # Workspace in config
    custom_workspace = tmp_path / "xdg_p"
    custom_workspace.mkdir()
    config_content = f'workspace = "{str(custom_workspace)}"\n'

    # Create config in XDG_CONFIG_HOME
    config_file = xdg_home / "cloner.toml"
    config_file.write_text(config_content)

    # Test
    url = "git@github.com:org/repo.git"
    target = clone_or_cd(url)

    assert target == custom_workspace / "org" / "repo"


def test_git_user_global_config(monkeypatch, tmp_path, mock_subprocess):
    """Global [git] section sets user.name and user.email on clone."""
    workspace = tmp_path / "p"
    workspace.mkdir()
    monkeypatch.setenv("CLONER_WORKSPACE", str(workspace))

    config_content = '[git]\nname = "Global User"\nemail = "global@example.com"\n'

    config_dir = tmp_path / ".config"
    config_dir.mkdir()
    config_file = config_dir / "cloner.toml"
    config_file.write_text(config_content)

    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    url = "git@github.com:org/repo.git"
    target = clone_or_cd(url)

    assert target == workspace / "org" / "repo"
    assert [
        "git",
        "-C",
        str(target),
        "config",
        "user.name",
        "Global User",
    ] in mock_subprocess
    assert [
        "git",
        "-C",
        str(target),
        "config",
        "user.email",
        "global@example.com",
    ] in mock_subprocess


def test_git_user_per_prefix_config(monkeypatch, tmp_path, mock_subprocess):
    """Per-prefix table entry sets git user for matching repos."""
    workspace = tmp_path / "p"
    workspace.mkdir()
    monkeypatch.setenv("CLONER_WORKSPACE", str(workspace))

    custom_dest = tmp_path / "work"
    custom_dest.mkdir()

    config_content = (
        f'["github.com/work-org"]\n'
        f'path = "{str(custom_dest)}"\n'
        f'git_name = "Work User"\n'
        f'git_email = "work@corp.com"\n'
    )

    config_dir = tmp_path / ".config"
    config_dir.mkdir()
    config_file = config_dir / "cloner.toml"
    config_file.write_text(config_content)

    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    url = "git@github.com:work-org/project.git"
    target = clone_or_cd(url)

    assert target == custom_dest / "project"
    assert [
        "git",
        "-C",
        str(target),
        "config",
        "user.name",
        "Work User",
    ] in mock_subprocess
    assert [
        "git",
        "-C",
        str(target),
        "config",
        "user.email",
        "work@corp.com",
    ] in mock_subprocess


def test_git_user_per_prefix_overrides_global(monkeypatch, tmp_path, mock_subprocess):
    """Per-prefix git user overrides the global [git] section."""
    workspace = tmp_path / "p"
    workspace.mkdir()
    monkeypatch.setenv("CLONER_WORKSPACE", str(workspace))

    custom_dest = tmp_path / "work"
    custom_dest.mkdir()

    config_content = (
        f'[git]\nname = "Global"\nemail = "global@example.com"\n\n'
        f'["github.com/work-org"]\n'
        f'path = "{str(custom_dest)}"\n'
        f'git_name = "Work"\n'
        f'git_email = "work@corp.com"\n'
    )

    config_dir = tmp_path / ".config"
    config_dir.mkdir()
    config_file = config_dir / "cloner.toml"
    config_file.write_text(config_content)

    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    url = "git@github.com:work-org/project.git"
    target = clone_or_cd(url)

    assert ["git", "-C", str(target), "config", "user.name", "Work"] in mock_subprocess
    assert [
        "git",
        "-C",
        str(target),
        "config",
        "user.email",
        "work@corp.com",
    ] in mock_subprocess


def test_git_user_no_config_no_calls(monkeypatch, tmp_path, mock_subprocess):
    """No git config calls when no git user is configured."""
    workspace = tmp_path / "p"
    workspace.mkdir()
    monkeypatch.setenv("CLONER_WORKSPACE", str(workspace))

    config_content = f'workspace = "{str(workspace)}"\n'

    config_dir = tmp_path / ".config"
    config_dir.mkdir()
    config_file = config_dir / "cloner.toml"
    config_file.write_text(config_content)

    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    url = "git@github.com:org/repo.git"
    clone_or_cd(url)

    assert mock_subprocess == []


def test_git_user_applied_on_existing_repo(monkeypatch, tmp_path, mock_subprocess):
    """Git user config is applied even when repo already exists."""
    workspace = tmp_path / "p"
    workspace.mkdir()
    monkeypatch.setenv("CLONER_WORKSPACE", str(workspace))

    config_content = '[git]\nname = "User"\nemail = "user@example.com"\n'

    config_dir = tmp_path / ".config"
    config_dir.mkdir()
    config_file = config_dir / "cloner.toml"
    config_file.write_text(config_content)

    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Pre-create the repo directory
    repo_dir = workspace / "org" / "repo"
    (repo_dir / ".git").mkdir(parents=True)

    url = "git@github.com:org/repo.git"
    clone_or_cd(url)

    assert [
        "git",
        "-C",
        str(repo_dir),
        "config",
        "user.name",
        "User",
    ] in mock_subprocess
    assert [
        "git",
        "-C",
        str(repo_dir),
        "config",
        "user.email",
        "user@example.com",
    ] in mock_subprocess


def test_git_signing_key_global(monkeypatch, tmp_path, mock_subprocess):
    """Global [git] section sets user.signingKey on clone."""
    workspace = tmp_path / "p"
    workspace.mkdir()
    monkeypatch.setenv("CLONER_WORKSPACE", str(workspace))

    config_content = (
        '[git]\nname = "User"\nemail = "u@e.com"\nsigning_key = "ABCDEF1234567890"\n'
    )

    config_dir = tmp_path / ".config"
    config_dir.mkdir()
    (config_dir / "cloner.toml").write_text(config_content)

    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    target = clone_or_cd("git@github.com:org/repo.git")

    assert [
        "git",
        "-C",
        str(target),
        "config",
        "user.signingKey",
        "ABCDEF1234567890",
    ] in mock_subprocess


def test_git_signing_key_per_prefix(monkeypatch, tmp_path, mock_subprocess):
    """Per-prefix table entry sets signing key for matching repos."""
    workspace = tmp_path / "p"
    workspace.mkdir()
    monkeypatch.setenv("CLONER_WORKSPACE", str(workspace))

    custom_dest = tmp_path / "work"
    custom_dest.mkdir()

    config_content = (
        f'["github.com/work-org"]\n'
        f'path = "{str(custom_dest)}"\n'
        f'git_name = "Work"\n'
        f'git_email = "work@corp.com"\n'
        f'git_signing_key = "WORKKEY123"\n'
    )

    config_dir = tmp_path / ".config"
    config_dir.mkdir()
    (config_dir / "cloner.toml").write_text(config_content)

    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    target = clone_or_cd("git@github.com:work-org/project.git")

    assert [
        "git",
        "-C",
        str(target),
        "config",
        "user.signingKey",
        "WORKKEY123",
    ] in mock_subprocess


def test_git_signing_key_per_prefix_overrides_global(
    monkeypatch, tmp_path, mock_subprocess
):
    """Per-prefix signing key overrides the global one."""
    workspace = tmp_path / "p"
    workspace.mkdir()
    monkeypatch.setenv("CLONER_WORKSPACE", str(workspace))

    custom_dest = tmp_path / "work"
    custom_dest.mkdir()

    config_content = (
        f'[git]\nsigning_key = "GLOBALKEY"\n\n'
        f'["github.com/work-org"]\n'
        f'path = "{str(custom_dest)}"\n'
        f'git_signing_key = "WORKKEY"\n'
    )

    config_dir = tmp_path / ".config"
    config_dir.mkdir()
    (config_dir / "cloner.toml").write_text(config_content)

    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    target = clone_or_cd("git@github.com:work-org/project.git")

    assert [
        "git",
        "-C",
        str(target),
        "config",
        "user.signingKey",
        "WORKKEY",
    ] in mock_subprocess
    # Ensure global key is NOT set
    assert [
        "git",
        "-C",
        str(target),
        "config",
        "user.signingKey",
        "GLOBALKEY",
    ] not in mock_subprocess
