from __future__ import annotations
import subprocess
from dataclasses import dataclass
from repo_detect import RepoConfig


@dataclass
class ValidationResult:
    passed: bool
    reason: str


def run_build_gate(cfg: RepoConfig, cwd: str) -> ValidationResult:
    if not cfg.build_cmd:
        return ValidationResult(passed=True, reason="skipped — no build command detected")
    result = subprocess.run(
        cfg.build_cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=300
    )
    if result.returncode != 0:
        return ValidationResult(passed=False, reason=result.stderr or result.stdout)
    return ValidationResult(passed=True, reason="build succeeded")


def run_test_gate(cfg: RepoConfig, cwd: str) -> ValidationResult:
    if not cfg.test_cmd:
        return ValidationResult(passed=True, reason="skipped — no test command detected")
    result = subprocess.run(
        cfg.test_cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=300
    )
    if result.returncode != 0:
        return ValidationResult(passed=False, reason=result.stdout or result.stderr)
    return ValidationResult(passed=True, reason="tests passed")
