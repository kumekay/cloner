from pathlib import Path

import pytest

from cloner.core import clone_or_cd


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Ensure tests are isolated from the user's environment."""
    monkeypatch.delenv("CLONER_WORKSPACE", raising=False)
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)


def test_config_mapping_host_and_user(monkeypatch, tmp_path):
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

    # We need to mock subprocess.run because we don't want to actually clone
    import subprocess

    class MockResult:
        returncode = 0

    def mock_run(args, **kwargs):
        # Create the .git dir to simulate successful clone
        path = Path(args[3])
        (path / ".git").mkdir(parents=True)
        return MockResult()

    monkeypatch.setattr(subprocess, "run", mock_run)

    # Test mapping for org
    url = "git@github.com:myorg/repo.git"
    target = clone_or_cd(url)

    assert target == custom_dest / "repo"
    assert target.exists()


def test_config_mapping_host_only(monkeypatch, tmp_path):
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

    import subprocess

    class MockResult:
        returncode = 0

    def mock_run(args, **kwargs):
        path = Path(args[3])
        (path / ".git").mkdir(parents=True)
        return MockResult()

    monkeypatch.setattr(subprocess, "run", mock_run)

    # Test host-only mapping
    url = "https://gitlab.com/company/project.git"
    target = clone_or_cd(url)

    assert target == custom_dest / "company" / "project"


def test_config_mapping_self_hosted(monkeypatch, tmp_path):
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

    import subprocess

    class MockResult:
        returncode = 0

    def mock_run(args, **kwargs):
        path = Path(args[3])
        (path / ".git").mkdir(parents=True)
        return MockResult()

    monkeypatch.setattr(subprocess, "run", mock_run)

    # Test self-hosted example
    url = "ssh://git@git.example.com:2222/user/repo.git"
    target = clone_or_cd(url)

    assert target == custom_dest / "user" / "repo"


def test_config_workspace(monkeypatch, tmp_path):
    # Setup custom workspace in config
    custom_workspace = tmp_path / "custom_p"
    custom_workspace.mkdir()

    config_content = f'workspace = "{str(custom_workspace)}"\n'

    config_dir = tmp_path / ".config"
    config_dir.mkdir()
    config_file = config_dir / "cloner.toml"
    config_file.write_text(config_content)

    # Mock Path.home()
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    import subprocess

    class MockResult:
        returncode = 0

    def mock_run(args, **kwargs):
        path = Path(args[3])
        (path / ".git").mkdir(parents=True)
        return MockResult()

    monkeypatch.setattr(subprocess, "run", mock_run)

    # Test that it uses the workspace from config
    url = "git@github.com:org/repo.git"
    target = clone_or_cd(url)

    assert target == custom_workspace / "org" / "repo"


def test_config_xdg_home(monkeypatch, tmp_path):
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

    import subprocess

    class MockResult:
        returncode = 0

    def mock_run(args, **kwargs):
        path = Path(args[3])
        (path / ".git").mkdir(parents=True)
        return MockResult()

    monkeypatch.setattr(subprocess, "run", mock_run)

    # Test
    url = "git@github.com:org/repo.git"
    target = clone_or_cd(url)

    assert target == custom_workspace / "org" / "repo"
