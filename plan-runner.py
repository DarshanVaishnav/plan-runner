#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path


def parse_args():
    p = argparse.ArgumentParser(description="Autonomous plan executor for Claude Code")
    p.add_argument("plan", type=Path, help="Path to PLAN.md")
    p.add_argument("--repo", type=Path, default=None, help="Repo root (default: plan file's directory)")
    p.add_argument("--build", default=None, help="Override build command")
    p.add_argument("--test", default=None, help="Override test command")
    p.add_argument("--dry-run", action="store_true", help="Print tasks without executing")
    return p.parse_args()


def main():
    args = parse_args()
    if not args.plan.exists():
        print(f"Error: plan file not found: {args.plan}", file=sys.stderr)
        sys.exit(1)
    repo_root = args.repo or args.plan.parent
    print(f"Plan: {args.plan}")
    print(f"Repo: {repo_root}")
    print(f"Dry run: {args.dry_run}")


if __name__ == "__main__":
    main()
