"""Repo-only commands must fail clearly outside a source clone.

`verify`, `audit`, and `docs_stats_check` read pyproject.toml,
tests/, README.md, and docs/. In a wheel install none of those exist, so each
command exits with one clear message instead of a confusing missing-file
error. Also covers `gpu_stack.__version__`.
"""

import pytest

import gpu_stack
import gpu_stack.cli_common as cli_common
from gpu_stack import docs_stats_check
from gpu_stack.cli import main


def test_version_is_a_nonempty_string():
    assert isinstance(gpu_stack.__version__, str)
    assert gpu_stack.__version__
    assert "__version__" in gpu_stack.__all__


def test_require_source_tree_accepts_this_repo():
    root = cli_common._require_source_tree("audit")
    assert (root / "pyproject.toml").is_file()


def test_require_source_tree_rejects_a_directory_without_a_source_tree(tmp_path):
    with pytest.raises(SystemExit) as excinfo:
        cli_common._require_source_tree("audit", tmp_path)
    message = str(excinfo.value)
    assert "source clone" in message
    assert "pyproject.toml" in message


def test_audit_fails_clearly_when_not_in_a_source_tree(tmp_path, monkeypatch):
    monkeypatch.setattr(cli_common, "_repo_root", lambda: tmp_path)
    with pytest.raises(SystemExit) as excinfo:
        main(["audit"])
    assert "source clone" in str(excinfo.value)


def test_verify_fails_clearly_when_cwd_is_not_a_source_tree(tmp_path):
    with pytest.raises(SystemExit) as excinfo:
        main(["verify", "--cwd", str(tmp_path)])
    assert "source clone" in str(excinfo.value)


def test_docs_stats_check_fails_clearly_when_not_in_a_source_tree(tmp_path):
    with pytest.raises(SystemExit) as excinfo:
        docs_stats_check.main(["--repo-root", str(tmp_path)])
    assert "source clone" in str(excinfo.value)
