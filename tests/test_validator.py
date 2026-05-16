from unittest.mock import patch, MagicMock
from repo_detect import RepoConfig
from validator import run_build_gate, run_test_gate, ValidationResult


def _proc(returncode=0, stdout="", stderr=""):
    p = MagicMock()
    p.returncode = returncode
    p.stdout = stdout
    p.stderr = stderr
    return p


def test_build_gate_passes_on_exit_0():
    cfg = RepoConfig(build_cmd="make build", test_cmd=None)
    with patch("validator.subprocess.run", return_value=_proc(returncode=0)):
        result = run_build_gate(cfg, cwd="/tmp")
    assert result.passed is True


def test_build_gate_fails_on_nonzero():
    cfg = RepoConfig(build_cmd="make build", test_cmd=None)
    with patch("validator.subprocess.run", return_value=_proc(returncode=1, stderr="missing symbol")):
        result = run_build_gate(cfg, cwd="/tmp")
    assert result.passed is False
    assert "missing symbol" in result.reason


def test_build_gate_skips_when_no_build_cmd():
    cfg = RepoConfig(build_cmd=None, test_cmd=None)
    result = run_build_gate(cfg, cwd="/tmp")
    assert result.passed is True
    assert "skipped" in result.reason.lower()


def test_test_gate_passes_on_exit_0():
    cfg = RepoConfig(build_cmd=None, test_cmd="pytest")
    with patch("validator.subprocess.run", return_value=_proc(returncode=0, stdout="5 passed")):
        result = run_test_gate(cfg, cwd="/tmp")
    assert result.passed is True


def test_test_gate_fails_on_nonzero():
    cfg = RepoConfig(build_cmd=None, test_cmd="pytest")
    with patch("validator.subprocess.run", return_value=_proc(returncode=1, stdout="1 failed")):
        result = run_test_gate(cfg, cwd="/tmp")
    assert result.passed is False
    assert "1 failed" in result.reason


def test_test_gate_skips_when_no_test_cmd():
    cfg = RepoConfig(build_cmd=None, test_cmd=None)
    result = run_test_gate(cfg, cwd="/tmp")
    assert result.passed is True
    assert "skipped" in result.reason.lower()
