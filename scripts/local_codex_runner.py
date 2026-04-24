from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


REPO = "SSMakers/reviewMaker"
TASK_LABEL = "codex-task"
RUNNING_LABEL = "codex-running"
DONE_LABEL = "codex-done"
FAILED_LABEL = "codex-failed"
STATE_DIR = ".codex-runner"
LOG_PATH = "logs/local_codex_runner.log"
DEFAULT_ALLOWED_UNTRACKED = {"selfsigned.crt"}
DEFAULT_TEST_COMMAND = (
    "python3 -m py_compile main.py auto_updater.py api_worker.py "
    "image_mapping.py review_article_builder.py review_preflight.py ui/main_window.py"
)
CODEX_MODE_WORKSPACE = "workspace-write"
CODEX_MODE_FULL_AUTO = "full-auto"
CODEX_MODE_DANGER = "danger-full-access"


@dataclass(frozen=True)
class Issue:
    number: int
    title: str
    body: str
    url: str
    labels: set[str]


class RunnerError(Exception):
    pass


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def append_log(message: str, *, workdir: Path):
    log_path = workdir / LOG_PATH
    log_path.parent.mkdir(parents=True, exist_ok=True)
    line = f"[{now()}] {message}"
    log_path.write_text(
        (log_path.read_text(encoding="utf-8") if log_path.exists() else "") + line + "\n",
        encoding="utf-8",
    )
    print(line)


def run(
    command: list[str],
    *,
    workdir: Path,
    check: bool = True,
    timeout: int | None = None,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=workdir,
        input=input_text,
        text=True,
        capture_output=True,
        timeout=timeout,
    )
    if check and result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise RunnerError(f"Command failed: {shlex.join(command)}\n{detail}")
    return result


def load_json(command: list[str], *, workdir: Path) -> Any:
    result = run(command, workdir=workdir)
    return json.loads(result.stdout or "null")


def resolve_git_root(path: str) -> Path:
    start = Path(path).expanduser().resolve()
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=start,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        raise RunnerError(f"git repository root를 찾지 못했습니다: {start}\n{result.stderr.strip()}")
    return Path(result.stdout.strip()).resolve()


def slugify(text: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9가-힣]+", "-", text).strip("-").lower()
    return value[:48] or "task"


def issue_from_json(data: dict[str, Any]) -> Issue:
    labels = {label["name"] for label in data.get("labels", []) if "name" in label}
    return Issue(
        number=int(data["number"]),
        title=str(data["title"]),
        body=str(data.get("body") or ""),
        url=str(data.get("url") or ""),
        labels=labels,
    )


def ensure_tools(workdir: Path):
    for command in ("git", "gh", "codex"):
        run(["which", command], workdir=workdir)
    run(["gh", "auth", "status"], workdir=workdir)
    run(["codex", "--help"], workdir=workdir)


def ensure_labels(repo: str, workdir: Path):
    labels = [
        (TASK_LABEL, "2563eb", "Local Codex runner task queue"),
        (RUNNING_LABEL, "f59e0b", "Local Codex runner is processing this issue"),
        (DONE_LABEL, "16a34a", "Local Codex runner created a PR"),
        (FAILED_LABEL, "dc2626", "Local Codex runner failed"),
    ]
    for name, color, description in labels:
        existing = run(["gh", "label", "list", "-R", repo, "--search", name, "--json", "name"], workdir=workdir)
        found = any(label.get("name") == name for label in json.loads(existing.stdout or "[]"))
        if not found:
            run(
                [
                    "gh",
                    "label",
                    "create",
                    name,
                    "-R",
                    repo,
                    "--color",
                    color,
                    "--description",
                    description,
                ],
                workdir=workdir,
            )


def find_candidate_issues(repo: str, workdir: Path, issue_number: int | None = None) -> list[Issue]:
    fields = "number,title,body,labels,url"
    if issue_number is not None:
        data = load_json(["gh", "issue", "view", str(issue_number), "-R", repo, "--json", fields], workdir=workdir)
        return [issue_from_json(data)]

    data = load_json(
        [
            "gh",
            "issue",
            "list",
            "-R",
            repo,
            "--state",
            "open",
            "--label",
            TASK_LABEL,
            "--json",
            fields,
            "--limit",
            "20",
        ],
        workdir=workdir,
    )
    return [issue_from_json(item) for item in data]


def is_processable(issue: Issue) -> bool:
    blocked = {RUNNING_LABEL, DONE_LABEL, FAILED_LABEL}
    return issue.title.startswith("[Slack Task]") and TASK_LABEL in issue.labels and not issue.labels.intersection(blocked)


def git_status_lines(workdir: Path) -> list[str]:
    result = run(["git", "status", "--short"], workdir=workdir)
    return [line for line in result.stdout.splitlines() if line.strip()]


def is_allowed_untracked_path(path_text: str, allowed_untracked: set[str]) -> bool:
    normalized = Path(path_text).as_posix()
    basename = Path(path_text).name
    return normalized in allowed_untracked or basename in allowed_untracked


def assert_clean_worktree(workdir: Path, allowed_untracked: set[str]):
    unsafe = []
    for line in git_status_lines(workdir):
        path = line[3:].strip()
        if line.startswith("?? ") and is_allowed_untracked_path(path, allowed_untracked):
            continue
        if path.startswith(f"{STATE_DIR}/"):
            continue
        unsafe.append(line)
    if unsafe:
        raise RunnerError("작업 전 git worktree가 깨끗하지 않습니다.\n" + "\n".join(unsafe))


def changed_paths_for_commit(workdir: Path, allowed_untracked: set[str]) -> list[str]:
    paths = []
    for line in git_status_lines(workdir):
        path = line[3:].strip()
        if line.startswith("?? ") and is_allowed_untracked_path(path, allowed_untracked):
            continue
        if path.startswith(f"{STATE_DIR}/"):
            continue
        paths.append(path)
    return paths


def set_issue_labels(repo: str, issue: Issue, workdir: Path, *, add: list[str] | None = None, remove: list[str] | None = None):
    command = ["gh", "issue", "edit", str(issue.number), "-R", repo]
    for label in add or []:
        command.extend(["--add-label", label])
    for label in remove or []:
        command.extend(["--remove-label", label])
    run(command, workdir=workdir)


def comment_issue(repo: str, issue_number: int, body: str, workdir: Path):
    run(["gh", "issue", "comment", str(issue_number), "-R", repo, "--body", body], workdir=workdir)


def build_codex_prompt(issue: Issue, *, allow_git_operations: bool) -> str:
    git_instruction = (
        "필요하면 git 명령을 직접 실행해도 됩니다. 단 main 브랜치에 직접 push하지 말고 현재 작업 브랜치만 사용하세요."
        if allow_git_operations
        else "commit, push, PR 생성은 local runner가 수행하므로 Codex는 하지 마세요."
    )
    return f"""GitHub Issue #{issue.number}을 처리하세요.

작업 전 반드시 Index.md와 docs/release-process.md를 읽으세요.
main 브랜치에 직접 push하지 마세요.
{git_instruction}
필요한 코드/문서 수정과 가능한 검증만 수행하세요.
테스트 또는 검증 결과를 마지막 응답에 요약하세요.
관련 문서나 Index.md 업데이트가 필요하면 함께 수정하세요.

Issue title:
{issue.title}

Issue URL:
{issue.url}

Issue body:
{issue.body}
"""


def codex_mode_args(mode: str) -> list[str]:
    if mode == CODEX_MODE_DANGER:
        return ["--dangerously-bypass-approvals-and-sandbox"]
    if mode == CODEX_MODE_FULL_AUTO:
        return ["--full-auto"]
    return ["--sandbox", "workspace-write"]


def run_codex(issue: Issue, workdir: Path, timeout: int, mode: str, allow_git_operations: bool):
    state_dir = workdir / STATE_DIR
    state_dir.mkdir(parents=True, exist_ok=True)
    output_path = state_dir / f"issue-{issue.number}-codex-last-message.txt"
    prompt = build_codex_prompt(issue, allow_git_operations=allow_git_operations)
    command = [
        "codex",
        "exec",
        "-C",
        str(workdir),
        *codex_mode_args(mode),
        "--output-last-message",
        str(output_path),
        prompt,
    ]
    return run(command, workdir=workdir, timeout=timeout)


def checkout_task_branch(issue: Issue, workdir: Path):
    branch = f"codex/issue-{issue.number}-{slugify(issue.title)}"
    run(["git", "fetch", "origin"], workdir=workdir)
    run(["git", "checkout", "main"], workdir=workdir)
    run(["git", "pull", "--ff-only", "origin", "main"], workdir=workdir)
    existing = run(["git", "branch", "--list", branch], workdir=workdir)
    if existing.stdout.strip():
        run(["git", "checkout", branch], workdir=workdir)
    else:
        run(["git", "checkout", "-b", branch], workdir=workdir)
    return branch


def create_pr(repo: str, issue: Issue, branch: str, workdir: Path) -> str:
    body = "\n".join(
        [
            "Change type: internal",
            "Version bump: none",
            "Current version: see version.py",
            "Next version: unchanged unless modified by Codex",
            "Tested:",
            "- Local Codex runner executed configured checks.",
            "Release notes:",
            "- See linked issue.",
            "Risk:",
            "- Review generated changes before merge.",
            "",
            f"Closes #{issue.number}",
        ]
    )
    result = run(
        [
            "gh",
            "pr",
            "create",
            "-R",
            repo,
            "--base",
            "main",
            "--head",
            branch,
            "--title",
            issue.title.replace("[Slack Task]", "[Codex]").strip(),
            "--body",
            body,
        ],
        workdir=workdir,
    )
    return result.stdout.strip()


def process_issue(args: argparse.Namespace, issue: Issue, workdir: Path):
    append_log(f"처리 시작: Issue #{issue.number} {issue.title}", workdir=workdir)
    if args.dry_run:
        append_log(f"dry-run: 처리 대상 Issue URL: {issue.url}", workdir=workdir)
        return

    assert_clean_worktree(workdir, set(args.allowed_untracked))
    set_issue_labels(args.repo, issue, workdir, add=[RUNNING_LABEL], remove=[FAILED_LABEL])
    try:
        branch = checkout_task_branch(issue, workdir)
        run_codex(
            issue,
            workdir,
            timeout=args.codex_timeout_sec,
            mode=args.codex_mode,
            allow_git_operations=args.allow_codex_git,
        )

        if args.test_command and not args.skip_tests:
            append_log(f"테스트 실행: {args.test_command}", workdir=workdir)
            run(["bash", "-lc", args.test_command], workdir=workdir, timeout=args.test_timeout_sec)

        changed_paths = changed_paths_for_commit(workdir, set(args.allowed_untracked))
        if not changed_paths:
            raise RunnerError("Codex 실행 후 commit할 변경사항이 없습니다.")

        run(["git", "add", "--", *changed_paths], workdir=workdir)
        run(["git", "commit", "-m", f"Handle issue #{issue.number}"], workdir=workdir)
        run(["git", "push", "-u", "origin", branch], workdir=workdir)
        pr_url = create_pr(args.repo, issue, branch, workdir)

        comment_issue(args.repo, issue.number, f"Local Codex runner가 PR을 생성했습니다.\n\n{pr_url}", workdir)
        set_issue_labels(args.repo, issue, workdir, add=[DONE_LABEL], remove=[RUNNING_LABEL])
        append_log(f"처리 완료: Issue #{issue.number}, PR: {pr_url}", workdir=workdir)
    except Exception as exc:
        set_issue_labels(args.repo, issue, workdir, add=[FAILED_LABEL], remove=[RUNNING_LABEL])
        comment_issue(args.repo, issue.number, f"Local Codex runner 처리 실패:\n\n```text\n{exc}\n```", workdir)
        append_log(f"처리 실패: Issue #{issue.number}: {exc}", workdir=workdir)
        raise


def select_issue(args: argparse.Namespace, workdir: Path) -> Issue | None:
    issues = find_candidate_issues(args.repo, workdir, args.issue)
    for issue in issues:
        if args.issue is not None or is_processable(issue):
            return issue
    return None


def run_once(args: argparse.Namespace, workdir: Path):
    ensure_tools(workdir)
    ensure_labels(args.repo, workdir)
    issue = select_issue(args, workdir)
    if issue is None:
        append_log("처리할 codex-task Issue가 없습니다.", workdir=workdir)
        return
    process_issue(args, issue, workdir)


def dashboard(args: argparse.Namespace, workdir: Path):
    try:
        from rich.console import Console
        from rich.live import Live
        from rich.panel import Panel
        from rich.table import Table
    except ImportError as exc:
        raise RunnerError("dashboard 모드는 rich가 필요합니다. `pip install rich` 후 다시 실행하세요.") from exc

    console = Console()
    ensure_tools(workdir)
    ensure_labels(args.repo, workdir)
    last_message = "대기 중"

    def render():
        table = Table(title="Local Codex Runner")
        table.add_column("Field")
        table.add_column("Value")
        table.add_row("Repo", args.repo)
        table.add_row("Mode", "dashboard")
        table.add_row("Poll interval", f"{args.poll_interval_sec}s")
        table.add_row("Last update", now())
        table.add_row("Status", last_message)
        return Panel(table)

    with Live(render(), console=console, refresh_per_second=1) as live:
        while True:
            issue = select_issue(args, workdir)
            if issue is None:
                last_message = "처리할 Issue 없음"
                live.update(render())
                time.sleep(args.poll_interval_sec)
                continue
            last_message = f"Issue #{issue.number} 처리 시작"
            live.update(render())
            process_issue(args, issue, workdir)
            last_message = f"Issue #{issue.number} 처리 완료"
            live.update(render())
            if args.once:
                return


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Local Codex runner for Slack-created GitHub Issues")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--once", action="store_true", help="Process one issue and exit")
    mode.add_argument("--watch", action="store_true", help="Poll continuously")
    mode.add_argument("--dashboard", action="store_true", help="Show a Rich dashboard while polling")
    parser.add_argument("--dry-run", action="store_true", help="Show selected issue without modifying anything")
    parser.add_argument("--issue", type=int, help="Process a specific issue number")
    parser.add_argument("--repo", default=REPO)
    parser.add_argument("--workdir", default=os.getcwd())
    parser.add_argument("--poll-interval-sec", type=int, default=60)
    parser.add_argument("--codex-timeout-sec", type=int, default=1800)
    parser.add_argument("--test-timeout-sec", type=int, default=300)
    parser.add_argument("--test-command", default=DEFAULT_TEST_COMMAND)
    parser.add_argument("--skip-tests", action="store_true")
    parser.add_argument("--allowed-untracked", action="append", default=list(DEFAULT_ALLOWED_UNTRACKED))
    parser.add_argument(
        "--codex-mode",
        choices=[CODEX_MODE_WORKSPACE, CODEX_MODE_FULL_AUTO, CODEX_MODE_DANGER],
        default=CODEX_MODE_DANGER,
        help="Codex execution permission mode. Default gives Codex full local permissions.",
    )
    parser.add_argument(
        "--allow-codex-git",
        action="store_true",
        help="Allow Codex prompt to perform git operations. Runner still creates the final PR.",
    )
    args = parser.parse_args()
    if not args.once and not args.watch and not args.dashboard:
        args.once = True
    return args


def main():
    args = parse_args()
    workdir = resolve_git_root(args.workdir)
    try:
        if args.dashboard:
            dashboard(args, workdir)
        elif args.watch:
            while True:
                run_once(args, workdir)
                time.sleep(args.poll_interval_sec)
        else:
            run_once(args, workdir)
    except KeyboardInterrupt:
        print("\n중단했습니다.")
    except Exception as exc:
        append_log(f"runner 오류: {exc}", workdir=workdir)
        sys.exit(1)


if __name__ == "__main__":
    main()
