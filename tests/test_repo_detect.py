import json
from pathlib import Path
from repo_detect import detect_repo_config, RepoConfig


def test_detects_npm(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({
        "scripts": {"build": "tsc", "test": "jest"}
    }))
    cfg = detect_repo_config(tmp_path)
    assert cfg.build_cmd == "npm run build"
    assert cfg.test_cmd == "npm test"


def test_detects_makefile(tmp_path):
    (tmp_path / "Makefile").write_text("build:\n\tgo build ./...\ntest:\n\tgo test ./...\n")
    cfg = detect_repo_config(tmp_path)
    assert cfg.build_cmd == "make build"
    assert cfg.test_cmd == "make test"


def test_detects_xcodeproj(tmp_path):
    xcodeproj = tmp_path / "MyApp.xcodeproj"
    xcodeproj.mkdir()
    cfg = detect_repo_config(tmp_path)
    assert "xcodebuild" in cfg.build_cmd
    assert "MyApp" in cfg.build_cmd
    assert "xcodebuild test" in cfg.test_cmd


def test_detects_pyproject(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool.pytest.ini_options]\n")
    cfg = detect_repo_config(tmp_path)
    assert cfg.test_cmd == "python3 -m pytest"
    assert cfg.build_cmd is None


def test_override_respected(tmp_path):
    cfg = detect_repo_config(tmp_path, build_override="make custom", test_override="./run_tests.sh")
    assert cfg.build_cmd == "make custom"
    assert cfg.test_cmd == "./run_tests.sh"


def test_no_artifacts_returns_none(tmp_path):
    cfg = detect_repo_config(tmp_path)
    assert cfg.build_cmd is None
    assert cfg.test_cmd is None
