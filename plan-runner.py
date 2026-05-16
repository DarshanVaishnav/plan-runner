#!/usr/bin/env python3
from __future__ import annotations
import argparse
import signal
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from context_builder import build_context
from executor import CreditExhaustedError, run_claude
from plan_parser import Task, TaskStatus, parse_plan, write_status
from repo_detect import RepoConfig, detect_repo_config
from validator import (
    ValidationResult,
    run_build_gate,
    run_criteria_gate,
    run_diff_review_gate,
    run_test_gate,
)

MAX_RETRIES = 2
LOG_FILE = Path("runner.log")


def parse_args():
    p = argparse.ArgumentParser(description="Autonomous plan executor for Claude Code")
    p.add_argument("plan", type=Path, help="Path to PLAN.md")
    p.add_argument("--repo", type=Path, default=None)
    p.add_argument("--build", default=None)
    p.add_argument("--test", default=None)
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args()


def log(msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with LOG_FILE.open("a") as f:
        f.write(line + "\n")


def get_diff(repo_root: Path) -> str:
    result = subprocess.run(
        ["git", "diff", "HEAD"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    return result.stdout


def validate_task(task: Task, cfg: RepoConfig, repo_root: Path) -> tuple[bool, str]:
    cwd = str(repo_root)
    diff = get_diff(repo_root)

    gates = [
        (lambda: run_build_gate(cfg, cwd), "build"),
        (lambda: run_test_gate(cfg, cwd), "tests"),
        (lambda: run_criteria_gate(task, diff, cwd), "criteria"),
        (lambda: run_diff_review_gate(task, diff, cwd), "diff-review"),
    ]

    for gate_fn, gate_name in gates:
        result: ValidationResult = gate_fn()
        if not result.passed:
            log(f"  ✗ {gate_name}: {result.reason}")
            return False, f"{gate_name} failed: {result.reason}"
        log(f"  ✓ {gate_name}")

    return True, "all gates passed"


def run_loop(plan_path: Path, repo_root: Path, cfg: RepoConfig, dry_run: bool) -> None:
    def handle_exit(sig, frame):
        log("Interrupted — saving state and exiting.")
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_exit)

    tasks = parse_plan(plan_path)
    pending = [t for t in tasks if t.status == TaskStatus.PENDING]
    completed = [t for t in tasks if t.status == TaskStatus.DONE]
    blocked = [t for t in tasks if t.status == TaskStatus.BLOCKED]

    log(f"Plan loaded: {len(pending)} pending, {len(completed)} done, {len(blocked)} blocked")

    if dry_run:
        for t in pending:
            print(f"  [ ] {t.title}")
        return

    for task in pending:
        log(f"\n→ Task: {task.title}")
        retries = 0
        failure_reason: str | None = None

        while retries <= MAX_RETRIES:
            context = build_context(
                task=task,
                completed=completed,
                blocked=blocked,
                repo_root=repo_root,
            )
            if failure_reason:
                context += f"\n\n## Previous Attempt Failed\n{failure_reason}\nFix this and try again."

            try:
                run_claude(context, cwd=str(repo_root))
            except CreditExhaustedError as e:
                log(f"Credits exhausted: {e}")
                log("State saved. Remaining tasks still marked pending in plan.")
                return

            valid, reason = validate_task(task, cfg, repo_root)
            if valid:
                write_status(plan_path, task, TaskStatus.DONE)
                completed.append(task)
                log(f"✓ Done: {task.title}")
                break
            else:
                retries += 1
                failure_reason = reason
                if retries <= MAX_RETRIES:
                    log(f"  Retry {retries}/{MAX_RETRIES}: {reason}")
                else:
                    write_status(plan_path, task, TaskStatus.BLOCKED, reason=reason)
                    blocked.append(task)
                    log(f"✗ Blocked after {MAX_RETRIES} retries: {task.title}")
                    break

    log(f"\nDone. {len(completed)} completed, {len(blocked)} blocked.")


def main():
    args = parse_args()
    if not args.plan.exists():
        print(f"Error: plan file not found: {args.plan}", file=sys.stderr)
        sys.exit(1)

    repo_root = args.repo or args.plan.parent
    cfg = detect_repo_config(repo_root, build_override=args.build, test_override=args.test)
    log(f"Build: {cfg.build_cmd or 'none'} | Test: {cfg.test_cmd or 'none'}")

    run_loop(args.plan, repo_root, cfg, args.dry_run)


if __name__ == "__main__":
    main()
