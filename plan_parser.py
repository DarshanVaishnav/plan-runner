"""Plan file parser for plan-runner.

Splits a markdown plan on '## Task:' headers, parses each block,
and supports in-place status patching.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class TaskStatus(str, Enum):
    PENDING = "[ ]"
    DONE = "[x]"
    BLOCKED = "[~]"

    @classmethod
    def from_str(cls, s: str) -> "TaskStatus":
        s = s.strip()
        for member in cls:
            if member.value == s:
                return member
        raise ValueError(f"Unknown status: {s!r}")


@dataclass
class Task:
    title: str
    status: TaskStatus
    files: list[str]
    acceptance: list[str]
    blocker: str | None = None
    raw_block: str = ""


def _split_blocks(text: str) -> list[str]:
    """Split file text into per-task blocks on '## Task:' headers.

    Each returned string includes the header line and everything up to
    (but not including) the next header or end-of-file.
    """
    # Split keeping the delimiter via a lookahead
    parts = re.split(r"(?=^## Task:)", text, flags=re.MULTILINE)
    # Filter out empty strings (e.g. text before first task)
    return [p for p in parts if p.strip().startswith("## Task:")]


def _parse_block(block: str) -> Task:
    lines = block.splitlines()

    # Title — first line: "## Task: <title>"
    title_match = re.match(r"^##\s+Task:\s+(.+)$", lines[0])
    if not title_match:
        raise ValueError(f"Bad task header: {lines[0]!r}")
    title = title_match.group(1).strip()

    status = TaskStatus.PENDING
    files: list[str] = []
    acceptance: list[str] = []
    blocker: str | None = None

    in_acceptance = False

    for line in lines[1:]:
        # Strip trailing whitespace for matching, but keep raw
        stripped = line.rstrip()

        if stripped.startswith("Status:"):
            raw_status = stripped[len("Status:"):].strip()
            status = TaskStatus.from_str(raw_status)
            in_acceptance = False

        elif stripped.startswith("Files:"):
            raw_files = stripped[len("Files:"):].strip()
            files = [f.strip() for f in raw_files.split(",") if f.strip()]
            in_acceptance = False

        elif stripped.startswith("Blocker:"):
            blocker = stripped[len("Blocker:"):].strip()
            in_acceptance = False

        elif stripped == "Acceptance:":
            in_acceptance = True

        elif in_acceptance and stripped.startswith("- "):
            acceptance.append(stripped[2:].strip())

        elif stripped in ("---", ""):
            # Section divider or blank line — keep in_acceptance if inside it
            # A blank line doesn't end acceptance list, but --- does
            if stripped == "---":
                in_acceptance = False

    return Task(
        title=title,
        status=status,
        files=files,
        acceptance=acceptance,
        blocker=blocker,
        raw_block=block,
    )


def parse_plan(path: Path) -> list[Task]:
    """Parse a plan markdown file and return a list of Task objects."""
    text = path.read_text()
    blocks = _split_blocks(text)
    return [_parse_block(b) for b in blocks]


def write_status(
    path: Path,
    task: Task,
    status: TaskStatus,
    reason: str | None = None,
) -> None:
    """Patch the status (and optional blocker) of a task block in-place.

    Raises ValueError if the task's raw_block is no longer present in the
    file (stale object — file was modified after parse).
    """
    text = path.read_text()

    # Stale check: the exact raw_block must still be present
    if task.raw_block not in text:
        raise ValueError(
            f"Task '{task.title}' is stale — the plan file has changed since it was parsed."
        )

    old_block = task.raw_block

    # 1. Patch the Status line inside the block
    new_block = re.sub(
        r"^(Status:\s*)(\[[ x~]\])(.*)$",
        lambda m: f"{m.group(1)}{status.value}{m.group(3)}",
        old_block,
        flags=re.MULTILINE,
    )

    # 2. Handle Blocker line
    has_blocker_line = bool(re.search(r"^Blocker:", new_block, re.MULTILINE))

    if status == TaskStatus.BLOCKED and reason is not None:
        blocker_line = f"Blocker: {reason}"
        if has_blocker_line:
            # Replace existing Blocker: line
            new_block = re.sub(
                r"^Blocker:.*$",
                blocker_line,
                new_block,
                flags=re.MULTILINE,
            )
        else:
            # Insert after the Status line
            new_block = re.sub(
                r"^(Status:.*\n)",
                rf"\1{blocker_line}\n",
                new_block,
                flags=re.MULTILINE,
            )
    elif status != TaskStatus.BLOCKED and has_blocker_line:
        # Remove stale Blocker line when un-blocking
        new_block = re.sub(r"^Blocker:.*\n?", "", new_block, flags=re.MULTILINE)

    # 3. Replace the old block with the patched one
    new_text = text.replace(old_block, new_block, 1)
    path.write_text(new_text)
