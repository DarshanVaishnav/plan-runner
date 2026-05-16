from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class RepoConfig:
    build_cmd: str | None
    test_cmd: str | None


def detect_repo_config(
    repo_root: Path,
    build_override: str | None = None,
    test_override: str | None = None,
) -> RepoConfig:
    build_cmd = build_override
    test_cmd = test_override

    if build_cmd is not None and test_cmd is not None:
        return RepoConfig(build_cmd=build_cmd, test_cmd=test_cmd)

    # npm / package.json
    pkg = repo_root / "package.json"
    if pkg.exists():
        data = json.loads(pkg.read_text())
        scripts = data.get("scripts", {})
        if build_cmd is None and "build" in scripts:
            build_cmd = "npm run build"
        if test_cmd is None and "test" in scripts:
            test_cmd = "npm test"

    # Xcode project
    xcodeprojs = list(repo_root.glob("*.xcodeproj"))
    if xcodeprojs:
        scheme = xcodeprojs[0].stem
        if build_cmd is None:
            build_cmd = f"xcodebuild -scheme {scheme} -configuration Debug build"
        if test_cmd is None:
            test_cmd = f"xcodebuild test -scheme {scheme} -destination 'platform=iOS Simulator,name=iPhone 16'"

    # Makefile
    makefile = repo_root / "Makefile"
    if makefile.exists():
        text = makefile.read_text()
        if build_cmd is None and ("\nbuild:" in text or text.startswith("build:")):
            build_cmd = "make build"
        if test_cmd is None and ("\ntest:" in text or text.startswith("test:")):
            test_cmd = "make test"

    # pyproject.toml / setup.py (pytest)
    if (repo_root / "pyproject.toml").exists() or (repo_root / "setup.py").exists():
        if test_cmd is None:
            test_cmd = "python3 -m pytest"

    return RepoConfig(build_cmd=build_cmd, test_cmd=test_cmd)
