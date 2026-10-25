"""Project 9: a harness2 adapter whose executor is Claude Code (`claude -p`).

Three small bookkeeping ledgers form one domain. The starting harness (h0/) has a
defective script; the method must find the defects from the evidence alone.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

if sys.platform == "win32":
    # ponytail: harness2 imports fcntl for one summary lock (schedule.py:294); a 1-byte
    # msvcrt lock covers one process. Use WSL for parallel workers.
    import msvcrt
    import types

    def _flock(f, op):
        f.seek(0)
        msvcrt.locking(f.fileno(), msvcrt.LK_LOCK if op == 2 else msvcrt.LK_UNLCK, 1)

    sys.modules.setdefault("fcntl", types.SimpleNamespace(LOCK_EX=2, LOCK_UN=8, flock=_flock))

from harness2.core import tree
from harness2.core.proposer import Proposer, _parse_json
from harness2.core.spec import BenchPrompts, BenchSpec, ChannelSpec
from harness2.substrate.codex import CODEX_SURFACE

if sys.platform == "win32":
    # read_tree keys use the OS separator (tree.py:140); the validators and the stub
    # filter expect "/". This is tree.read_tree with as_posix().
    def _read_tree_posix(surface, d, *, rejected=None):
        d, out, stubs = Path(d), {}, tree._stub_paths(surface)
        for p in sorted(d.rglob("*")) if d.is_dir() else []:
            rel = p.relative_to(d).as_posix()
            if not p.is_file() or "__pycache__" in p.parts or rel in stubs:
                continue
            if not tree.is_allowed(surface, rel):
                if rejected is not None:
                    rejected.append(rel)
                continue
            out[rel] = p.read_text(encoding="utf-8", errors="replace")
        return out

    tree.read_tree = _read_tree_posix

HERE = Path(__file__).resolve().parent
EXECUTOR_MODEL = os.environ.get("P9_EXECUTOR_MODEL", "haiku")
IMPROVER_MODEL = os.environ.get("P9_IMPROVER_MODEL", "sonnet")
# Project-scope settings and no MCP: the user's settings, hooks and skills stay out.
ISOLATION = ["--setting-sources", "project", "--strict-mcp-config", "--no-session-persistence"]

# task -> (ledger.csv, expected total). The expected totals never reach the task folder.
TASKS = {
    "ledger-1": ("amount,status\n100.25,posted\n-20.10,posted\n5.00,posted\n", "85.15"),
    "ledger-2": (
        'amount,status\n"1,250.00",posted\n(300.50),posted\n-49.50,posted\n12.00,posted\n',
        "912.00",
    ),
    "ledger-3": (
        'amount,status\n40.00,posted\n-15.25,posted\n999.99,void\n(4.75),posted\n"2,000.00",void\n',
        "20.00",
    ),
}
PROMPT = (
    "Reconcile ledger.csv. Sum the signed amounts. A value in parentheses is negative. "
    "Skip rows whose status is void. Write one line, `Total: <amount>` with two decimal "
    "places, to answer.txt."
)


class ClaudeCodeLayout:
    """The core needs only .name and .surface(). The Codex layout has one always-on file,
    a skills folder and a hooks file, as Claude Code does; execute() maps it."""

    name = "cc"

    def surface(self):
        return CODEX_SURFACE


class LedgerAdapter:
    def __init__(self, root: Path, *, dry: bool = False):
        self.root = root
        self.dry = dry  # dry: run the harness script directly instead of `claude -p`
        self.substrate = ClaudeCodeLayout()
        channel = ChannelSpec("claude_cli", IMPROVER_MODEL)
        self.spec = BenchSpec(
            name="p9",
            runs_root=root / "runs",
            install_mode="codex_root",
            prompts=BenchPrompts(
                work="reconcile signed amounts in small bookkeeping ledgers",
                deliverable_word="answer file",
            ),
            channels={"proposer": channel, "selector": channel},
            leak_globs=("expected*", "answer_key*"),
        )
        for task_id, (ledger, _) in TASKS.items():
            src = self.task_files(task_id)
            src.mkdir(parents=True, exist_ok=True)
            (src / "ledger.csv").write_text(ledger, encoding="utf-8")

    def tasks(self, split: str = "all") -> list[str]:
        return list(TASKS)

    def domain_of(self, task_id: str) -> str:
        return "bookkeeping"

    def task_prompt(self, task_id: str) -> str:
        return PROMPT

    def task_files(self, task_id: str) -> Path:
        return self.root / "sources" / task_id

    def base_harness(self) -> Path:
        return HERE / "h0"

    def validate_tree(self, harness: dict[str, str]) -> None:
        if not harness.get("AGENTS.md", "").strip():
            raise ValueError("AGENTS.md must hold the instructions; it becomes CLAUDE.md")

    def _workspace(self, task_id: str, harness_dir: Path, ws: Path) -> None:
        """Install the harness the way Claude Code reads it."""
        shutil.copytree(self.task_files(task_id), ws)
        h = Path(harness_dir)
        shutil.copy(h / "AGENTS.md", ws / "CLAUDE.md")
        for src, dst in (("scripts", "scripts"), (".agents", ".agents"),
                         (".agents/skills", ".claude/skills")):
            if (h / src).is_dir():
                shutil.copytree(h / src, ws / dst, dirs_exist_ok=True)
        if (h / ".codex/hooks.json").is_file():  # same schema as Claude Code's "hooks" key
            (ws / ".claude").mkdir(exist_ok=True)
            shutil.copy(h / ".codex/hooks.json", ws / ".claude/settings.json")

    def execute(self, task_id, harness_dir, run_id, *, timeout=None) -> Path:
        run_dir = self.root / "executions" / run_id
        if (run_dir / "exit.json").is_file():  # idempotent by run_id
            return run_dir
        shutil.rmtree(run_dir, ignore_errors=True)
        ws = run_dir / "workspace"
        self._workspace(task_id, harness_dir or self.base_harness(), ws)
        stream = run_dir / "stream.jsonl"
        if self.dry:
            rc = _dry_run(ws, stream)
        else:
            cmd = [shutil.which("claude") or "claude", "-p", self.task_prompt(task_id),
                   "--model", EXECUTOR_MODEL, "--output-format", "stream-json", "--verbose",
                   "--dangerously-skip-permissions", *ISOLATION]  # sandbox only (limit 10)
            with open(stream, "w", encoding="utf-8") as out:
                rc = subprocess.run(cmd, cwd=ws, stdout=out, stderr=subprocess.STDOUT,
                                    timeout=timeout or 900).returncode
        (run_dir / "exit.json").write_text(json.dumps({"returncode": rc}), encoding="utf-8")
        return run_dir

    def delivered(self, run_dir: Path) -> bool:
        return (run_dir / "workspace/answer.txt").is_file()

    def trajectory(self, run_dir: Path, *, obs_trunc: int) -> str:
        out = []
        for raw in (run_dir / "stream.jsonl").read_text(encoding="utf-8").splitlines():
            try:
                event = json.loads(raw)
            except ValueError:
                continue
            content = (event.get("message") or {}).get("content")
            for part in content if isinstance(content, list) else []:
                kind = part.get("type")
                if kind == "tool_use":
                    out.append(f"[ACTION] {part['name']} {json.dumps(part.get('input'))}")
                elif kind == "text" and event.get("type") == "assistant":
                    out.append(f"[ACTION] message: {part['text']}")
                elif kind == "tool_result":
                    body = part.get("content")
                    if isinstance(body, list):
                        body = "\n".join(b.get("text", "") for b in body if isinstance(b, dict))
                    tag = "[ERROR]" if part.get("is_error") else "[OBSERVATION]"
                    out.append(f"{tag} {str(body)[:obs_trunc]}")
        return "\n".join(out)

    def deliverable_text(self, run_dir: Path) -> str:
        p = run_dir / "workspace/answer.txt"
        return p.read_text(encoding="utf-8") if p.is_file() else ""

    def deliverable_files(self, run_dir: Path) -> dict[str, str]:
        return {"answer.txt": self.deliverable_text(run_dir)}

    def score(self, run_dir: Path, task_id: str) -> dict | None:
        got = self.deliverable_text(Path(run_dir)).strip()
        want = f"Total: {TASKS[task_id][1]}"
        return {"score": float(got == want), "expected": want, "got": got}


def _dry_run(ws: Path, stream: Path) -> int:
    """Stand-in executor: run the harness script and log it in the stream-json shape."""
    cmd = "python3 scripts/summarize.py ledger.csv"
    p = subprocess.run([sys.executable, "scripts/summarize.py", "ledger.csv"], cwd=ws,
                       capture_output=True, text=True, timeout=60)
    if p.returncode == 0:
        (ws / "answer.txt").write_text(p.stdout, encoding="utf-8")
    events = [
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Bash", "input": {"command": cmd}}]}},
        {"type": "user", "message": {"content": [
            {"type": "tool_result", "content": p.stdout + p.stderr,
             "is_error": p.returncode != 0}]}},
    ]
    stream.write_text("".join(json.dumps(e) + "\n" for e in events), encoding="utf-8")
    return p.returncode


class ClaudeProposer(Proposer):
    """The claude_cli channel, on the user's own Claude login instead of Vertex AI."""

    def env(self) -> dict[str, str]:
        e = dict(os.environ)
        e["ANTHROPIC_MODEL"] = self.spec.model
        return e

    def _claude_cli(self, cwd: Path, mission: str, system: str, wall: int):
        # Copy of Proposer._claude_cli (harness2/core/proposer.py) plus ISOLATION. The
        # system text always goes on stdin: Windows caps a command line at 32,767 chars.
        cmd = [shutil.which("claude") or "claude", "--dangerously-skip-permissions", "-p",
               "--output-format", "json", "--effort", self.spec.effort, *ISOLATION]
        stdin = mission
        if system:
            stdin = f"# SYSTEM INSTRUCTIONS\n\n{system}\n\n# END\n\n{mission}"
            cmd += ["--append-system-prompt",
                    "Follow the SYSTEM INSTRUCTIONS block at the top of the message."]
        p = subprocess.run(cmd, input=stdin, cwd=cwd, env=self.env(), text=True,
                           encoding="utf-8", capture_output=True, timeout=wall)
        payload = _parse_json(p.stdout)
        text = str(payload.get("result") or payload.get("text") or "")
        err = ""
        if payload.get("is_error") or payload.get("subtype") not in (None, "success"):
            err = f"CLI error: {payload.get('subtype')} {text[:200]}"
            text = ""
        elif p.returncode != 0 and not text.strip():
            err = f"rc={p.returncode}: {(p.stderr or '')[-300:]}"
        return text, float(payload.get("total_cost_usd") or 0.0), err
