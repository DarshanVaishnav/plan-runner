from pathlib import Path
from plan_parser import Task, TaskStatus
from context_builder import build_context


def _make_task(title="Add hello", files=None, acceptance=None):
    return Task(
        title=title,
        status=TaskStatus.PENDING,
        files=files or ["src/hello.py"],
        acceptance=acceptance or ["hello() returns 'hello world'"],
    )


def test_context_contains_task_title():
    ctx = build_context(
        task=_make_task(),
        completed=[],
        blocked=[],
        repo_root=Path("/tmp"),
    )
    assert "Add hello" in ctx


def test_context_contains_acceptance_criteria():
    ctx = build_context(
        task=_make_task(),
        completed=[],
        blocked=[],
        repo_root=Path("/tmp"),
    )
    assert "hello() returns" in ctx


def test_context_includes_completed_summaries():
    done = [_make_task("Previous task")]
    ctx = build_context(
        task=_make_task(),
        completed=done,
        blocked=[],
        repo_root=Path("/tmp"),
    )
    assert "Previous task" in ctx
    assert "done" in ctx.lower()


def test_context_includes_blocker_log():
    blocked = [Task(
        title="Broken task",
        status=TaskStatus.BLOCKED,
        files=[],
        acceptance=[],
        blocker="missing import",
    )]
    ctx = build_context(
        task=_make_task(),
        completed=[],
        blocked=blocked,
        repo_root=Path("/tmp"),
    )
    assert "Broken task" in ctx
    assert "missing import" in ctx


def test_context_includes_anatomy_excerpt(tmp_path):
    anatomy = tmp_path / ".wolf" / "anatomy.md"
    anatomy.parent.mkdir()
    anatomy.write_text(
        "## src/\n- `hello.py` — greeting module (~50 tok)\n- `other.py` — unrelated (~30 tok)\n"
    )
    ctx = build_context(
        task=_make_task(files=["src/hello.py"]),
        completed=[],
        blocked=[],
        repo_root=tmp_path,
    )
    assert "greeting module" in ctx
    assert "unrelated" not in ctx


def test_context_excludes_anatomy_when_missing(tmp_path):
    ctx = build_context(
        task=_make_task(),
        completed=[],
        blocked=[],
        repo_root=tmp_path,
    )
    assert "Add hello" in ctx


def test_anatomy_does_not_match_filename_substrings(tmp_path):
    anatomy = tmp_path / ".wolf" / "anatomy.md"
    anatomy.parent.mkdir()
    anatomy.write_text(
        "## src/\n"
        "- `auth.py` — auth module (~40 tok)\n"
        "- `authenticator.py` — full auth class (~200 tok)\n"
    )
    ctx = build_context(
        task=_make_task(files=["src/auth.py"]),
        completed=[],
        blocked=[],
        repo_root=tmp_path,
    )
    assert "auth module" in ctx
    assert "full auth class" not in ctx
