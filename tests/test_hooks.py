import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from cloner.core import clone_or_cd, detect_hook_manager, install_hooks


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Ensure tests are isolated from the user's environment."""
    monkeypatch.delenv("CLONER_WORKSPACE", raising=False)
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)


# --- detect_hook_manager tests ---


def test_detect_lefthook_yml(tmp_path):
    (tmp_path / "lefthook.yml").touch()
    assert detect_hook_manager(tmp_path) == "lefthook"


def test_detect_lefthook_toml(tmp_path):
    (tmp_path / "lefthook.toml").touch()
    assert detect_hook_manager(tmp_path) == "lefthook"


def test_detect_pre_commit(tmp_path):
    (tmp_path / ".pre-commit-config.yaml").touch()
    assert detect_hook_manager(tmp_path) == "pre-commit"


def test_detect_husky(tmp_path):
    (tmp_path / ".husky").mkdir()
    assert detect_hook_manager(tmp_path) == "husky"


def test_detect_no_manager(tmp_path):
    assert detect_hook_manager(tmp_path) is None


def test_detect_lefthook_takes_precedence(tmp_path):
    """When multiple managers exist, lefthook is detected first."""
    (tmp_path / "lefthook.yml").touch()
    (tmp_path / ".pre-commit-config.yaml").touch()
    assert detect_hook_manager(tmp_path) == "lefthook"


# --- install_hooks unit tests ---


@pytest.fixture
def mock_subprocess(monkeypatch):
    """Mock subprocess.run to capture all calls."""

    class MockResult:
        returncode = 0

    calls = []

    def mock_run(args, **kwargs):
        calls.append(args)
        if args[:2] == ["git", "clone"]:
            path = Path(args[3])
            (path / ".git" / "hooks").mkdir(parents=True)
        return MockResult()

    monkeypatch.setattr(subprocess, "run", mock_run)
    return calls


def test_install_hooks_lefthook_yml(tmp_path, monkeypatch, mock_subprocess):
    (tmp_path / ".git" / "hooks").mkdir(parents=True)
    (tmp_path / "lefthook.yml").touch()
    monkeypatch.setattr(shutil, "which", lambda cmd: "/usr/bin/lefthook")

    install_hooks(tmp_path)

    assert ["lefthook", "install"] in mock_subprocess


def test_install_hooks_lefthook_toml(tmp_path, monkeypatch, mock_subprocess):
    (tmp_path / ".git" / "hooks").mkdir(parents=True)
    (tmp_path / "lefthook.toml").touch()
    monkeypatch.setattr(shutil, "which", lambda cmd: "/usr/bin/lefthook")

    install_hooks(tmp_path)

    assert ["lefthook", "install"] in mock_subprocess


def test_install_hooks_pre_commit(tmp_path, monkeypatch, mock_subprocess):
    (tmp_path / ".git" / "hooks").mkdir(parents=True)
    (tmp_path / ".pre-commit-config.yaml").touch()
    monkeypatch.setattr(shutil, "which", lambda cmd: "/usr/bin/pre-commit")

    install_hooks(tmp_path)

    assert ["pre-commit", "install"] in mock_subprocess


def test_install_hooks_husky(tmp_path, monkeypatch, mock_subprocess):
    (tmp_path / ".git" / "hooks").mkdir(parents=True)
    (tmp_path / ".git" / "config").write_text("[core]\n\trepositoryformatversion = 0\n")
    (tmp_path / ".husky").mkdir()
    monkeypatch.setattr(shutil, "which", lambda cmd: "/usr/bin/npx")

    install_hooks(tmp_path)

    assert ["npx", "husky"] in mock_subprocess


def test_install_hooks_skips_when_pre_commit_hook_exists(
    tmp_path, monkeypatch, mock_subprocess
):
    """Hooks are not re-installed when .git/hooks/pre-commit already exists."""
    (tmp_path / ".git" / "hooks").mkdir(parents=True)
    (tmp_path / ".git" / "hooks" / "pre-commit").write_text("#!/bin/sh\n# hook")
    (tmp_path / "lefthook.yml").touch()
    monkeypatch.setattr(shutil, "which", lambda cmd: "/usr/bin/lefthook")

    install_hooks(tmp_path)

    assert ["lefthook", "install"] not in mock_subprocess


def test_install_hooks_skips_husky_when_hooks_path_configured(
    tmp_path, monkeypatch, mock_subprocess
):
    """Husky hooks are not re-installed when core.hooksPath is already set."""
    (tmp_path / ".git" / "hooks").mkdir(parents=True)
    (tmp_path / ".git" / "config").write_text("[core]\n\thooksPath = .husky\n")
    (tmp_path / ".husky").mkdir()
    monkeypatch.setattr(shutil, "which", lambda cmd: "/usr/bin/npx")

    install_hooks(tmp_path)

    assert ["npx", "husky"] not in mock_subprocess


def test_install_hooks_skips_when_tool_not_available(
    tmp_path, monkeypatch, mock_subprocess
):
    """No install command is run when the tool binary is not found."""
    (tmp_path / ".git" / "hooks").mkdir(parents=True)
    (tmp_path / "lefthook.yml").touch()
    monkeypatch.setattr(shutil, "which", lambda cmd: None)

    install_hooks(tmp_path)

    assert mock_subprocess == []


def test_install_hooks_no_manager(tmp_path, mock_subprocess):
    """No install command is run when no hook manager is detected."""
    (tmp_path / ".git" / "hooks").mkdir(parents=True)

    install_hooks(tmp_path)

    assert mock_subprocess == []


def test_install_hooks_warns_on_nonzero_exit(tmp_path, monkeypatch, capsys):
    """A warning is printed to stderr when the install command fails."""
    (tmp_path / ".git" / "hooks").mkdir(parents=True)
    (tmp_path / "lefthook.yml").touch()
    monkeypatch.setattr(shutil, "which", lambda cmd: "/usr/bin/lefthook")

    class FailResult:
        returncode = 1

    monkeypatch.setattr(subprocess, "run", lambda args, **kwargs: FailResult())

    install_hooks(tmp_path)

    captured = capsys.readouterr()
    assert "Warning: lefthook install failed" in captured.err


def test_install_hooks_warns_on_exception(tmp_path, monkeypatch, capsys):
    """A warning is printed to stderr when subprocess.run raises."""
    (tmp_path / ".git" / "hooks").mkdir(parents=True)
    (tmp_path / "lefthook.yml").touch()
    monkeypatch.setattr(shutil, "which", lambda cmd: "/usr/bin/lefthook")

    def raise_error(args, **kwargs):
        raise OSError("spawn failed")

    monkeypatch.setattr(subprocess, "run", raise_error)

    install_hooks(tmp_path)

    captured = capsys.readouterr()
    assert "Warning: hook installation failed" in captured.err


@pytest.mark.parametrize(
    "filename,is_dir,which_cmd",
    [
        ("lefthook.yml", False, "lefthook"),
        (".pre-commit-config.yaml", False, "pre-commit"),
        (".husky", True, "npx"),
    ],
)
def test_install_hooks_redirects_stdout_to_stderr(
    tmp_path, monkeypatch, filename, is_dir, which_cmd
):
    """Hook installer stdout is redirected to stderr.

    The shell wrapper captures `clone`'s stdout to cd into the resulting dir,
    so any extra output on stdout (e.g. `pre-commit installed at ...`) breaks
    the cd. Hook installer output must go to stderr instead.
    """
    (tmp_path / ".git" / "hooks").mkdir(parents=True)
    if is_dir:
        (tmp_path / filename).mkdir()
    else:
        (tmp_path / filename).touch()
    monkeypatch.setattr(shutil, "which", lambda cmd: f"/usr/bin/{which_cmd}")

    captured_kwargs = []

    class MockResult:
        returncode = 0

    def mock_run(args, **kwargs):
        captured_kwargs.append(kwargs)
        return MockResult()

    monkeypatch.setattr(subprocess, "run", mock_run)

    install_hooks(tmp_path)

    assert len(captured_kwargs) == 1
    assert captured_kwargs[0].get("stdout") is sys.stderr


def test_install_hooks_passes_cwd(tmp_path, monkeypatch, mock_subprocess):
    """The install command is run with cwd set to the repo path."""
    (tmp_path / ".git" / "hooks").mkdir(parents=True)
    (tmp_path / ".pre-commit-config.yaml").touch()

    cwd_values = []
    original_mock = subprocess.run

    def capture_cwd(args, **kwargs):
        cwd_values.append(kwargs.get("cwd"))
        return original_mock(args, **kwargs)

    monkeypatch.setattr(subprocess, "run", capture_cwd)
    monkeypatch.setattr(shutil, "which", lambda cmd: "/usr/bin/pre-commit")

    install_hooks(tmp_path)

    assert str(tmp_path) in cwd_values


# --- Integration with clone_or_cd ---


def test_existing_repo_installs_lefthook(monkeypatch, tmp_path, mock_subprocess):
    """Hook installation is triggered when cd-ing to an existing repo with lefthook."""
    workspace = tmp_path / "p"
    workspace.mkdir()
    monkeypatch.setenv("CLONER_WORKSPACE", str(workspace))

    config_dir = tmp_path / ".config"
    config_dir.mkdir()
    (config_dir / "cloner.toml").write_text(f'workspace = "{workspace}"\n')
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Pre-create repo with lefthook config
    repo_dir = workspace / "org" / "repo"
    (repo_dir / ".git" / "hooks").mkdir(parents=True)
    (repo_dir / "lefthook.yml").touch()

    monkeypatch.setattr(shutil, "which", lambda cmd: "/usr/bin/lefthook")

    clone_or_cd("git@github.com:org/repo.git")

    assert ["lefthook", "install"] in mock_subprocess


def test_existing_repo_installs_pre_commit(monkeypatch, tmp_path, mock_subprocess):
    """Hook install is triggered for existing repo with pre-commit."""
    workspace = tmp_path / "p"
    workspace.mkdir()
    monkeypatch.setenv("CLONER_WORKSPACE", str(workspace))

    config_dir = tmp_path / ".config"
    config_dir.mkdir()
    (config_dir / "cloner.toml").write_text(f'workspace = "{workspace}"\n')
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Pre-create repo with pre-commit config
    repo_dir = workspace / "org" / "repo"
    (repo_dir / ".git" / "hooks").mkdir(parents=True)
    (repo_dir / ".pre-commit-config.yaml").touch()

    monkeypatch.setattr(shutil, "which", lambda cmd: "/usr/bin/pre-commit")

    clone_or_cd("git@github.com:org/repo.git")

    assert ["pre-commit", "install"] in mock_subprocess


def test_existing_repo_skips_when_hooks_installed(
    monkeypatch, tmp_path, mock_subprocess
):
    """No hook install when hooks are already set up in existing repo."""
    workspace = tmp_path / "p"
    workspace.mkdir()
    monkeypatch.setenv("CLONER_WORKSPACE", str(workspace))

    config_dir = tmp_path / ".config"
    config_dir.mkdir()
    (config_dir / "cloner.toml").write_text(f'workspace = "{workspace}"\n')
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Pre-create repo with hooks already installed
    repo_dir = workspace / "org" / "repo"
    (repo_dir / ".git" / "hooks").mkdir(parents=True)
    (repo_dir / ".git" / "hooks" / "pre-commit").write_text("#!/bin/sh\n# hook")
    (repo_dir / "lefthook.yml").touch()

    monkeypatch.setattr(shutil, "which", lambda cmd: "/usr/bin/lefthook")

    clone_or_cd("git@github.com:org/repo.git")

    assert ["lefthook", "install"] not in mock_subprocess
