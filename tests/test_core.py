from pathlib import Path

from cloner.core import load_config, normalize_url, parse_git_url


def test_parse_https_url():
    result = parse_git_url("https://github.com/kumekay/kumekay.com.git")
    assert result == Path("kumekay/kumekay.com")


def test_parse_https_url_no_git():
    result = parse_git_url("https://github.com/kumekay/repo")
    assert result == Path("kumekay/repo")


def test_parse_ssh_url():
    result = parse_git_url("git@github.com:kumekay/kumekay.com.git")
    assert result == Path("kumekay/kumekay.com")


def test_parse_ssh_nested_groups():
    result = parse_git_url("git@gitlab.com:group/subgroup/repo.git")
    assert result == Path("gitlab.com/group/subgroup/repo")


def test_parse_ssh_with_port():
    result = parse_git_url("ssh://git@gitea.example.com:2222/org/repo.git")
    assert result == Path("gitea.example.com/org/repo")


def test_parse_deeply_nested():
    result = parse_git_url("git@gitlab.com:org/team/project/repo.git")
    assert result == Path("gitlab.com/org/team/project/repo")


def test_parse_codeberg_https():
    result = parse_git_url("https://codeberg.org/uzu/strudel.git")
    assert result == Path("codeberg.org/uzu/strudel")


def test_parse_codeberg_ssh():
    result = parse_git_url("git@codeberg.org:uzu/strudel.git")
    assert result == Path("codeberg.org/uzu/strudel")


def test_parse_trailing_slash():
    result = parse_git_url("https://github.com/kumekay/repo.git/")
    assert result == Path("kumekay/repo")


def test_normalize_github_shorthand():
    result = normalize_url("kumekay/cloner")
    assert result == "git@github.com:kumekay/cloner.git"


def test_normalize_nested_shorthand():
    result = normalize_url("org/team/repo")
    assert result == "git@github.com:org/team/repo.git"


def test_load_config_creates_default_file_when_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    config_path = tmp_path / "cloner.toml"

    assert not config_path.exists()

    load_config()

    assert config_path.exists()


def test_load_config_default_file_contains_workspace(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    config_path = tmp_path / "cloner.toml"

    load_config()

    content = config_path.read_text()
    assert 'workspace = "~/p"' in content


def test_load_config_default_file_contains_commented_examples(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    config_path = tmp_path / "cloner.toml"

    load_config()

    content = config_path.read_text()
    assert "# Custom destination paths" in content
    assert '# "github.com/myorg"' in content


def test_load_config_returns_default_workspace_when_file_created(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    config = load_config()

    assert config.get("workspace") == "~/p"


def test_load_config_does_not_overwrite_existing_file(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    config_path = tmp_path / "cloner.toml"
    config_path.write_text('workspace = "~/custom"\n')

    config = load_config()

    assert config.get("workspace") == "~/custom"
