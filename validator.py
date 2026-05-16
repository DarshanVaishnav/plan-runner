from __future__ import annotations
import json
import re
import subprocess
from dataclasses import dataclass
from repo_detect import RepoConfig
from executor import run_claude
from plan_parser import Task


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


def run_criteria_gate(task: Task, diff: str, cwd: str) -> ValidationResult:
    if not task.acceptance:
        return ValidationResult(passed=True, reason="skipped — no acceptance criteria defined")

    criteria_list = "\n".join(f"- {c}" for c in task.acceptance)
    prompt = (
        f"You are a code reviewer. Given the following git diff and acceptance criteria, "
        f"check whether each criterion is met.\n\n"
        f"## Git Diff\n```\n{diff}\n```\n\n"
        f"## Acceptance Criteria\n{criteria_list}\n\n"
        f"Reply with ONLY valid JSON: "
        f'{{\"passed\": true/false, \"unmet\": [\"criterion text if unmet\"]}}'
    )
    result = run_claude(prompt, cwd=cwd)
    try:
        data = json.loads(_extract_json(result.output))
        if data.get("passed"):
            return ValidationResult(passed=True, reason="all criteria met")
        unmet = data.get("unmet", [])
        return ValidationResult(passed=False, reason="; ".join(unmet))
    except (json.JSONDecodeError, KeyError):
        return ValidationResult(passed=False, reason=f"criteria check parse error: {result.output[:200]}")


def run_diff_review_gate(task: Task, diff: str, cwd: str) -> ValidationResult:
    prompt = (
        f"You are a senior code reviewer. Did this git diff accomplish the task?\n\n"
        f"## Task\n{task.title}\n\n"
        f"## Git Diff\n```\n{diff}\n```\n\n"
        f"Reply with ONLY valid JSON: "
        f'{{\"passed\": true/false, \"reason\": \"one sentence\"}}'
    )
    result = run_claude(prompt, cwd=cwd)
    try:
        data = json.loads(_extract_json(result.output))
        if data.get("passed"):
            return ValidationResult(passed=True, reason=data.get("reason", "task accomplished"))
        return ValidationResult(passed=False, reason=data.get("reason", "reviewer rejected diff"))
    except (json.JSONDecodeError, KeyError):
        return ValidationResult(passed=False, reason=f"diff review parse error: {result.output[:200]}")


def _extract_json(text: str) -> str:
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        return match.group(1)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return match.group(0)
    return text
