from pathlib import Path
from plan_parser import parse_plan, write_status, Task, TaskStatus

FIXTURE = Path(__file__).parent / "fixtures" / "sample.md"


def test_parse_returns_three_tasks():
    tasks = parse_plan(FIXTURE)
    assert len(tasks) == 3


def test_pending_task_fields():
    tasks = parse_plan(FIXTURE)
    t = tasks[0]
    assert t.title == "Add hello function"
    assert t.status == TaskStatus.PENDING
    assert t.files == ["src/hello.py"]
    assert 'hello() returns "hello world"' in t.acceptance
    assert "Build passes" in t.acceptance


def test_done_task_status():
    tasks = parse_plan(FIXTURE)
    assert tasks[2].status == TaskStatus.DONE


def test_pending_tasks_filters_done(tmp_path):
    import shutil
    plan = tmp_path / "sample.md"
    shutil.copy(FIXTURE, plan)
    tasks = parse_plan(plan)
    pending = [t for t in tasks if t.status == TaskStatus.PENDING]
    assert len(pending) == 2


def test_write_status_marks_done(tmp_path):
    import shutil
    plan = tmp_path / "sample.md"
    shutil.copy(FIXTURE, plan)
    tasks = parse_plan(plan)
    write_status(plan, tasks[0], TaskStatus.DONE)
    reloaded = parse_plan(plan)
    assert reloaded[0].status == TaskStatus.DONE


def test_write_status_marks_blocked_with_reason(tmp_path):
    import shutil
    plan = tmp_path / "sample.md"
    shutil.copy(FIXTURE, plan)
    tasks = parse_plan(plan)
    write_status(plan, tasks[0], TaskStatus.BLOCKED, reason="build failed: missing import")
    reloaded = parse_plan(plan)
    assert reloaded[0].status == TaskStatus.BLOCKED
    assert reloaded[0].blocker == "build failed: missing import"


def test_write_status_double_blocked_replaces_blocker(tmp_path):
    import shutil
    plan = tmp_path / "sample.md"
    shutil.copy(FIXTURE, plan)
    tasks = parse_plan(plan)
    write_status(plan, tasks[0], TaskStatus.BLOCKED, reason="first reason")
    tasks = parse_plan(plan)
    write_status(plan, tasks[0], TaskStatus.BLOCKED, reason="second reason")
    reloaded = parse_plan(plan)
    assert reloaded[0].blocker == "second reason"
    assert plan.read_text().count("Blocker:") == 1


def test_write_status_stale_object_raises(tmp_path):
    import shutil
    plan = tmp_path / "sample.md"
    shutil.copy(FIXTURE, plan)
    tasks = parse_plan(plan)
    write_status(plan, tasks[0], TaskStatus.DONE)
    import pytest
    with pytest.raises(ValueError):
        write_status(plan, tasks[0], TaskStatus.BLOCKED, reason="whatever")
