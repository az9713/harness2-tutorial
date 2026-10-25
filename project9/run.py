"""Run Project 9: one domain of ledger tasks through harness2, then score the results.

    python run.py --dry            # no model calls; checks the level-2 path (free)
    python run.py                  # sequential mode, k = 1, 3 tasks (8 claude calls per task)
    python run.py --no-library     # same tasks with the library off, for comparison
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from adapter import TASKS, ClaudeProposer, LedgerAdapter
from harness2.core.proposer import Proposer, Reply
from harness2.core.schedule import mode_token, run_domain, run_task

FIXED = '''import csv
import sys
from decimal import Decimal


def amount(text):
    text = text.strip().replace(",", "")
    if text.startswith("(") and text.endswith(")"):
        return -Decimal(text[1:-1])
    return Decimal(text)


with open(sys.argv[1], newline="") as source:
    rows = [r for r in csv.DictReader(source) if r["status"].strip().lower() != "void"]
print(f"Total: {sum((amount(r['amount']) for r in rows), Decimal(0)):.2f}")
'''


class ScriptedProposer(Proposer):
    """Dry mode: fixed edits and replies, in the shapes the real sessions return."""

    def call(self, mission, context_dir, label, **kwargs) -> Reply:
        context, workspace = Path(context_dir), None
        if label.startswith("select."):
            first = sorted((context / "candidates").glob("*.md"))[0].stem
            text = f"<why>First candidate.</why>\n```choice\n{first}\n```"
        elif label.startswith("experience."):
            text = (
                "<edits>\ncomponent: scripts/summarize.py\ncandidates: inv1\n"
                "change: kept signs, parsed (x) and 1,000 forms, skipped void rows\n"
                "observed: the probe total matched the signed ledger\nverdict: helped\n</edits>\n"
                "<experience>\ncue: When a ledger has credits, (x) amounts or void rows\n"
                "lesson: Parse every amount form and keep the sign in scripts/summarize.py.\n"
                "evidence: The scripts/summarize.py row -- the base run dropped credits.\n"
                "confidence: high for this scripted contrast\n</experience>"
            )
        else:
            workspace = context / "harness"
            (workspace / "scripts/summarize.py").write_text(FIXED, encoding="utf-8")
            text = "<notes>Rewrote the amount parser: signs, parentheses, separators, void.</notes>"
        reply = Reply(label=label, text=text, ok=True, attempts=1, workspace=workspace)
        self._calls.append(reply)
        return reply


def scores(adapter: LedgerAdapter, runs_root: Path, tasks: list[str]) -> list[dict]:
    """Score each base run and each selected final, from the task summaries only."""
    rows = []
    for task in tasks:
        for summary in sorted(runs_root.glob(f"*/{task}/summary.json")):
            s = json.loads(summary.read_text(encoding="utf-8"))
            for b in s.get("base") or []:
                rows.append({"task": task, "run": b["label"], **adapter.score(Path(b["run_dir"]), task)})
            for mode, sel in (s.get("selections") or {}).items():
                if sel.get("chosen_run_dir"):
                    run = f"{mode} final ({sel.get('chosen_label')})"
                    rows.append({"task": task, "run": run,
                                 **adapter.score(Path(sel["chosen_run_dir"]), task)})
    return rows


def check_level2(runs_root: Path, tasks: list[str]) -> None:
    """Task i's first editor must see exactly the entries of tasks 1 .. i-1."""
    for i, task in enumerate(tasks[1:], 1):
        found = sorted(p.name for p in runs_root.glob(f"*/{task}/context/inv1/library/harnesses/*"))
        assert found == sorted(tasks[:i]), f"{task}: library holds {found}, expected {tasks[:i]}"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parent / "runs")
    ap.add_argument("--k", type=int, default=1)
    ap.add_argument("--mode", choices=("parallel", "sequential", "both"), default="sequential")
    ap.add_argument("--tasks", type=int, default=len(TASKS), help="first N tasks (default: all)")
    ap.add_argument("--no-library", action="store_true", help="library off (limit 8)")
    ap.add_argument("--dry", action="store_true", help="no model calls; scripted editors")
    args = ap.parse_args(argv)

    # A separate root for --no-library: execute() and the session cache reuse by run_id.
    root = (args.out / (("dry" if args.dry else "live") + ("-nolib" * args.no_library))).resolve()
    adapter = LedgerAdapter(root, dry=args.dry)
    channel = adapter.spec.channels["proposer"]
    prop = (ScriptedProposer if args.dry else ClaudeProposer)(channel, audit_dir=root / "audit")
    modes = ("agg", "seq") if args.mode == "both" else (mode_token(args.mode),)
    tasks = adapter.tasks()[: args.tasks]

    runs_root = adapter.spec.runs_root
    if args.no_library:
        for task in tasks:
            r = run_task(task, args.k, adapter=adapter, prop=prop, runs_root=runs_root,
                         modes=modes, libraries=None)
            print(f"  [no library] {r.status:<12} {task}", flush=True)
    else:
        result = run_domain(adapter.domain_of(tasks[0]), tasks, args.k, adapter=adapter,
                            prop=prop, runs_root=runs_root,
                            library_root=root / "library" / f"k{args.k}", modes=modes)
        print(f"{result['done']} done, {result['failed']} failed")
        if args.dry:
            check_level2(runs_root, tasks)
            print("level-2 check passed: each task's first editor saw the earlier tasks only")

    rows = scores(adapter, runs_root, tasks)
    (runs_root / "scores.json").write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    for r in rows:
        print(f"  {r['task']:<9} {r['run']:<22} score {r['score']:.0f}   got {r['got'] or '-'}")
    print(f"Scores: {runs_root / 'scores.json'}   Cost so far: see {root / 'audit'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
