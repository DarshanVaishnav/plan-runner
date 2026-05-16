from unittest.mock import patch, MagicMock
from repo_detect import RepoConfig
from validator import run_build_gate, run_test_gate, ValidationResult, run_criteria_gate, run_diff_review_gate
from plan_parser import Task, TaskStatus


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


def _make_task(acceptance=None):
    return Task(
        title="Add hello",
        status=TaskStatus.PENDING,
        files=["src/hello.py"],
        acceptance=acceptance or ["hello() returns 'hello world'", "Build passes"],
    )


def test_criteria_gate_passes_when_claude_says_yes():
    task = _make_task()
    with patch("validator.run_claude") as mock_claude:
        mock_claude.return_value = MagicMock(
            success=True, output='{"passed": true, "unmet": []}'
        )
        result = run_criteria_gate(task, diff="+ def hello(): return 'hello world'", cwd="/tmp")
    assert result.passed is True


def test_criteria_gate_fails_when_unmet_criteria():
    task = _make_task()
    with patch("validator.run_claude") as mock_claude:
        mock_claude.return_value = MagicMock(
            success=True,
            output='{"passed": false, "unmet": ["hello() returns \'hello world\'"]}'
        )
        result = run_criteria_gate(task, diff="+ def hello(): pass", cwd="/tmp")
    assert result.passed is False
    assert "hello() returns" in result.reason


def test_criteria_gate_passes_when_no_acceptance_criteria():
    task = Task(title="t", status=TaskStatus.PENDING, files=[], acceptance=[])
    result = run_criteria_gate(task, diff="any diff", cwd="/tmp")
    assert result.passed is True
    assert "skipped" in result.reason.lower()


def test_diff_review_gate_passes():
    task = _make_task()
    with patch("validator.run_claude") as mock_claude:
        mock_claude.return_value = MagicMock(
            success=True, output='{"passed": true, "reason": "task accomplished"}'
        )
        result = run_diff_review_gate(task, diff="+ def hello(): return 'hello world'", cwd="/tmp")
    assert result.passed is True


def test_diff_review_gate_fails():
    task = _make_task()
    with patch("validator.run_claude") as mock_claude:
        mock_claude.return_value = MagicMock(
            success=True,
            output='{"passed": false, "reason": "function body not implemented"}'
        )
        result = run_diff_review_gate(task, diff="+ def hello(): pass", cwd="/tmp")
    assert result.passed is False
    assert "not implemented" in result.reason
