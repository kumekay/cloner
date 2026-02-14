from pathlib import Path

from cloner.core import normalize_url, parse_git_url


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
    assert result == Path("group/subgroup/repo")


def test_parse_ssh_with_port():
    result = parse_git_url("ssh://git@gitea.example.com:2222/org/repo.git")
    assert result == Path("org/repo")


def test_parse_deeply_nested():
    result = parse_git_url("git@gitlab.com:org/team/project/repo.git")
    assert result == Path("org/team/project/repo")


def test_parse_trailing_slash():
    result = parse_git_url("https://github.com/kumekay/repo.git/")
    assert result == Path("kumekay/repo")


def test_normalize_github_shorthand():
    result = normalize_url("kumekay/cloner")
    assert result == "git@github.com:kumekay/cloner.git"


def test_normalize_nested_shorthand():
    result = normalize_url("org/team/repo")
    assert result == "git@github.com:org/team/repo.git"
