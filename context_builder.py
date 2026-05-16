from __future__ import annotations
from pathlib import Path
from plan_parser import Task


def build_context(
    task: Task,
    completed: list[Task],
    blocked: list[Task],
    repo_root: Path,
) -> str:
    parts: list[str] = []

    parts.append(f"# Current Task: {task.title}")
    parts.append("")
    if task.files:
        parts.append(f"Files: {', '.join(task.files)}")
    parts.append("")
    parts.append("## Acceptance Criteria")
    for criterion in task.acceptance:
        parts.append(f"- {criterion}")

    anatomy_excerpt = _extract_anatomy(repo_root, task.files)
    if anatomy_excerpt:
        parts.append("")
        parts.append("## Relevant Files (from anatomy.md)")
        parts.append(anatomy_excerpt)

    if completed:
        parts.append("")
        parts.append("## Completed Tasks")
        for t in completed:
            parts.append(f"- {t.title} — done")

    if blocked:
        parts.append("")
        parts.append("## Blocked Tasks (avoid these approaches)")
        for t in blocked:
            reason = f": {t.blocker}" if t.blocker else ""
            parts.append(f"- {t.title}{reason}")

    parts.append("")
    parts.append("Implement the current task. Commit your changes when done.")

    return "\n".join(parts)


def _extract_anatomy(repo_root: Path, task_files: list[str]) -> str:
    anatomy_path = repo_root / ".wolf" / "anatomy.md"
    if not anatomy_path.exists():
        return ""

    text = anatomy_path.read_text()
    matched_lines: list[str] = []

    for file_path in task_files:
        filename = Path(file_path).name
        for line in text.splitlines():
            if filename in line and line.strip().startswith("-"):
                matched_lines.append(line.strip())

    return "\n".join(matched_lines)
