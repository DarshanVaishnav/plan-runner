from __future__ import annotations
import subprocess
from dataclasses import dataclass

_CREDIT_SIGNALS = [
    "credit limit",
    "credits exhausted",
    "usage limit",
    "quota exceeded",
    "rate limit",
    "insufficient credits",
]


class CreditExhaustedError(Exception):
    pass


@dataclass
class ExecutionResult:
    success: bool
    output: str


def run_claude(prompt: str, cwd: str) -> ExecutionResult:
    result = subprocess.run(
        ["claude", "-p", prompt],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=600,
    )

    combined = (result.stdout + result.stderr).lower()
    if any(signal in combined for signal in _CREDIT_SIGNALS):
        raise CreditExhaustedError(result.stderr or result.stdout)

    if result.returncode != 0:
        return ExecutionResult(success=False, output=result.stderr or result.stdout)

    return ExecutionResult(success=True, output=result.stdout)
