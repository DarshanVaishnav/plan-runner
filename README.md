# plan-runner

Autonomous Claude Code plan executor. Reads a structured PLAN.md, executes each task via Claude Code subprocesses, validates completion through a 4-layer check, and loops until the plan is complete or credits are exhausted.

## Requirements

- Python 3.9+
- `claude` CLI on PATH (Claude Code)
- `pip install -r requirements.txt`

## Plan file format

```markdown
## Task: Add hello function
Status: [ ]
Files: src/hello.py
Acceptance:
- hello() returns "hello world"
- Build passes

---

## Task: ...
Status: [ ]
```

Status values: `[ ]` pending · `[x]` done · `[~]` blocked

Optional fields:
- `Blocker: <reason>` — automatically populated when a task is blocked after retries

## Usage

```bash
# Run plan to completion
python3 plan-runner.py PLAN.md

# Specify repo root explicitly
python3 plan-runner.py PLAN.md --repo /path/to/repo

# Override build/test commands
python3 plan-runner.py PLAN.md --build "xcodebuild -scheme MyApp" --test "xcodebuild test -scheme MyApp"

# Dry run — list pending tasks without executing
python3 plan-runner.py PLAN.md --dry-run
```

## Validation layers

Each task passes through 4 gates before being marked done:

1. **Build gate** — repo build command must exit 0
2. **Test gate** — test suite must be green
3. **Criteria gate** — Claude checks each `Acceptance:` item against the git diff
4. **Diff review gate** — second Claude call confirms the task is accomplished

If a gate fails, the task retries (up to 2 times) with the failure reason added to context. After 2 retries the task is marked `[~]` blocked with the failure reason stored in a `Blocker:` field, and the loop continues.

## Credit exhaustion & resumability

On credit exhaustion or SIGINT (Ctrl+C), the loop exits cleanly. Completed tasks are already marked `[x]` in the plan file — rerun `plan-runner.py` to resume from where it stopped.

## Token discipline

Each Claude subprocess receives only:

- Current task text (title + files + acceptance criteria)
- Relevant `anatomy.md` excerpts (scoped to task files, if `.wolf/anatomy.md` exists)
- One-liner summaries of completed tasks
- Blocked task log with failure reasons

No full conversation history is passed forward.

## Auto-detected build systems

| Artifact | Build command | Test command |
|----------|--------------|--------------|
| `package.json` (with `scripts`) | `npm run build` | `npm test` |
| `*.xcodeproj` | `xcodebuild -scheme <name> -configuration Debug build` | `xcodebuild test -scheme <name> -destination 'platform=iOS Simulator,name=iPhone 16'` |
| `Makefile` | `make build` | `make test` |
| `pyproject.toml` or `setup.py` | — | `python3 -m pytest` |

Overrides via `--build` and `--test` take precedence.
