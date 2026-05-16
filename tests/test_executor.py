from unittest.mock import patch, MagicMock
from executor import run_claude, ExecutionResult, CreditExhaustedError
import pytest


def _mock_proc(returncode=0, stdout="done", stderr=""):
    proc = MagicMock()
    proc.returncode = returncode
    proc.stdout = stdout
    proc.stderr = stderr
    return proc


def test_successful_execution_returns_result():
    with patch("executor.subprocess.run", return_value=_mock_proc()) as mock_run:
        result = run_claude("do something", cwd="/tmp")
    assert isinstance(result, ExecutionResult)
    assert result.success is True
    assert result.output == "done"


def test_nonzero_exit_returns_failure():
    with patch("executor.subprocess.run", return_value=_mock_proc(returncode=1, stderr="error")):
        result = run_claude("do something", cwd="/tmp")
    assert result.success is False
    assert "error" in result.output


def test_credit_exhaustion_in_stderr_raises():
    with patch("executor.subprocess.run", return_value=_mock_proc(
        returncode=1, stderr="Error: credit limit exceeded"
    )):
        with pytest.raises(CreditExhaustedError):
            run_claude("do something", cwd="/tmp")


def test_credit_exhaustion_in_stdout_raises():
    with patch("executor.subprocess.run", return_value=_mock_proc(
        returncode=1, stdout="Your usage limit has been reached"
    )):
        with pytest.raises(CreditExhaustedError):
            run_claude("do something", cwd="/tmp")


def test_prompt_passed_to_claude_cli():
    with patch("executor.subprocess.run", return_value=_mock_proc()) as mock_run:
        run_claude("my task prompt", cwd="/tmp")
    call_args = mock_run.call_args
    cmd = call_args[0][0]
    assert "claude" in cmd[0]
    assert "-p" in cmd
    assert "my task prompt" in cmd
