"""Check the Project 9 live-run evidence in this folder. Stdlib only; makes no model calls.

    python check.py

Each check prints one PASS line. The first failed check stops the script with exit code 1.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
E = Path(__file__).resolve().parent
H0 = E.parent / "h0"
TASKS = ("ledger-1", "ledger-2", "ledger-3")
EXPECTED = {"ledger-1": "85.15", "ledger-2": "912.00", "ledger-3": "20.00"}  # adapter.py:58-68
EXECUTOR = "claude-haiku-4-5-20251001"
RUNS = ("base1", "inv1", "dom1", "c1")
# The 12 sessions of this run, per task: INV editor, DOM editor, composer, reflector.
SESSIONS = {
    "ledger-1": ("inv1.a1.ab7b6c255e32957a", "dom1.a1.c992d0f3bd66ea82",
                 "c1.a1.a2425424fc7c3256", "experience.seq1.6c60282c3ab6b74c"),
    "ledger-2": ("inv1.a1.bb39859b1ca12b0f", "dom1.a1.351fffc916cdbb4b",
                 "c1.a1.27f0542c68faa130", "experience.seq1.13f99bcc0a51fe33"),
    "ledger-3": ("inv1.a1.ec9a8350d85c500a", "dom1.a1.d2c0ecc54aa96d60",
                 "c1.a1.02e8250ee07c9084", "experience.seq1.2ede31c65f4cf204"),
}
LIB = E / "library/k1/seq/bookkeeping"


def ok(msg: str) -> None:
    print(f"PASS  {msg}")


def text(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def run_dir(task: str, label: str) -> Path:
    return E / "executions" / ("p9-cc-agg1" if label == "base1" else "p9-cc-seq1") / task / label


def harness(task: str, label: str) -> Path:
    return E / "runs/p9-cc-seq1" / task / "harnesses" / ("base" if label == "base1" else label)


def events(task: str, label: str) -> list[dict]:
    return [json.loads(x) for x in text(run_dir(task, label) / "stream.jsonl").splitlines() if x.strip()]


def first_script_output(ev: list[dict]) -> str:
    """Last line of the output of the run's first scripts/summarize.py call ("" if none)."""
    ids, results = [], {}
    for e in ev:
        content = (e.get("message") or {}).get("content")
        for part in content if isinstance(content, list) else []:
            if part.get("type") == "tool_use" and "scripts/summarize.py" in str(part["input"].get("command", "")):
                ids.append(part["id"])
            elif part.get("type") == "tool_result":
                body = part.get("content")
                if isinstance(body, list):
                    body = "".join(b.get("text", "") for b in body if isinstance(b, dict))
                results[part["tool_use_id"]] = str(body)
    return results[ids[0]].strip().splitlines()[-1] if ids else ""


def script_total(script: Path, ledger: Path) -> str:
    out = subprocess.run([sys.executable, "-I", str(script), str(ledger)],
                         capture_output=True, text=True, timeout=60)
    return (out.stdout.strip() or out.stderr.strip()).splitlines()[-1]  # last line: total or error


def same_tree(a: Path, b: Path) -> bool:
    return all(text(a / f) == text(b / f) for f in ("AGENTS.md", "scripts/summarize.py"))


def check_hashes() -> None:
    lines = text(E / "SHA256SUMS").splitlines()
    for line in lines:
        digest, rel = line.split("  ", 1)
        assert hashlib.sha256((E / rel).read_bytes()).hexdigest() == digest, f"hash differs: {rel}"
    ok(f"SHA256SUMS: all {len(lines)} files match")


def check_level1(task: str) -> None:
    s = json.loads(text(E / "runs/p9-cc-agg1" / task / "summary.json"))
    seq = s["modes"]["seq"]
    led = seq["ledger"]
    assert (led["R"], led["P"]) == (led["expected_R"], led["expected_P"]) == (4, 3), led
    ok(f"{task}: ledger R = 4 task runs, P = 3 editor sessions, as planned for k = 1")

    assert same_tree(harness(task, "base1"), H0)
    for label in ("inv1", "dom1"):
        assert not same_tree(harness(task, label), H0), label
    ok(f"{task}: harnesses/base equals project9/h0; the inv1 and dom1 harnesses differ from it")

    for stage, sess in zip(seq["stages"], SESSIONS[task]):
        meta = json.loads(text(E / "audit" / f"{sess}.meta.json"))
        assert meta["label"].startswith(stage["label"]) and meta["ok"], meta
        assert (meta["channel"], meta["model"]) == ("claude_cli", "sonnet"), meta
        assert abs(meta["cost_usd"] - stage["usd"]) < 1e-6, (meta["cost_usd"], stage["usd"])
        assert stage["notes"][:200] in text(E / "audit" / f"{sess}.response.md")
    ok(f"{task}: Propose and Compose: sessions inv1 (INV), dom1 (DOM), c1 (COMPOSE) ran on Sonnet; "
       f"their replies and costs match summary.json")

    ledger = run_dir(task, "base1") / "workspace/ledger.csv"
    sids, edits, linked = set(), [], []
    for label in RUNS:
        ev = events(task, label)
        init = next(e for e in ev if e.get("subtype") == "init")  # a rate_limit_event can come first
        assert init["model"] == EXECUTOR and init["apiKeySource"] == "none", init["model"]
        assert ev[-1]["type"] == "result" and ev[-1]["is_error"] is False
        sids.add(init["session_id"])
        got = first_script_output(ev)
        if got:
            want = script_total(harness(task, label) / "scripts/summarize.py", ledger)
            assert got == want, (label, got, want)
            linked.append(label)
        edits += [label for e in ev for p in ((e.get("message") or {}).get("content") or [])
                  if isinstance(p, dict) and p.get("type") == "tool_use" and p["name"] == "Edit"]
    assert len(sids) == 4
    ok(f"{task}: Probe: 4 task runs (base1, inv1, dom1, c1), 4 session ids, model {EXECUTOR}, "
       f"apiKeySource none")
    ok(f"{task}: runs {', '.join(linked)}: the first script call printed the same last line "
       f"as that run's harness script prints here")
    if len(linked) < 4:
        print(f"NOTE  {task}: {', '.join(l for l in RUNS if l not in linked)} did not call the script")
    if edits:
        print(f"NOTE  {task}: {', '.join(edits)} edited scripts/summarize.py during the run (Edit tool)")

    sel = s["selections"]["seq"]
    assert sel["chosen_label"] == "c1" and sel["chosen_is_base"] is False, sel
    ok(f"{task}: Select chose c1 (k = 1: one final, so no selector session)")

    want = f"Total: {EXPECTED[task]}"
    scores = {r["run"]: r for r in json.loads(text(E / "runs/scores.json")) if r["task"] == task}
    for label, row in (("base1", "base1"), ("c1", "seq final (c1)")):
        got = text(run_dir(task, label) / "workspace/answer.txt").strip()
        assert scores[row]["got"] == got and scores[row]["score"] == float(got == want), scores[row]
    ok(f"{task}: scores.json agrees with answer.txt: base1 {scores['base1']['score']:.0f}, "
       f"c1 {scores['seq final (c1)']['score']:.0f} (expected {want})")

    h0_out = script_total(H0 / "scripts/summarize.py", ledger)
    c1_out = script_total(harness(task, "c1") / "scripts/summarize.py", ledger)
    assert c1_out == want, c1_out
    ok(f"{task}: re-run without a model: H0 script prints '{h0_out}', c1 script prints '{c1_out}'")


def check_level2() -> None:
    for i, task in enumerate(TASKS):
        s = json.loads(text(E / "runs/p9-cc-agg1" / task / "summary.json"))
        lesson = s["selections"]["seq"]["experience"]["lesson"]
        assert lesson in text(LIB / "harnesses" / task / "EXPERIENCE.md")
        assert lesson[:200] in text(E / "audit" / f"{SESSIONS[task][3]}.response.md")
        ok(f"{task}: the reflector session wrote its lesson to library/.../{task}/EXPERIENCE.md")

        assert same_tree(LIB / "harnesses" / task / "harness", harness(task, "c1"))
        ok(f"{task}: the library stores the c1 harness of {task}")

        seen = E / "runs/p9-cc-seq1" / task / "context/inv1/library/harnesses"
        names = sorted(p.name for p in seen.iterdir()) if seen.is_dir() else []
        assert names == list(TASKS[:i]), names
        for name in names:
            for f in (p for p in (seen / name).rglob("*") if p.is_file()):
                assert f.read_bytes() == (LIB / "harnesses" / name / f.relative_to(seen / name)).read_bytes()
        if names:
            ok(f"{task}: the INV editor's context held the library entries {names}, byte-equal")
        if i:
            assert same_tree(harness(task, "base1"), H0)
            assert not same_tree(harness(task, "base1"), harness(TASKS[i - 1], "c1"))
            ok(f"{task}: base1 restarted from H0, not from the c1 harness of {TASKS[i - 1]}")

    r2 = text(E / "audit" / f"{SESSIONS['ledger-2'][0]}.response.md")
    assert "library/harnesses/ledger-1/EXPERIENCE" in r2
    ok("ledger-2: the INV editor's reply cites library/harnesses/ledger-1/EXPERIENCE.md")
    r3 = text(E / "audit" / f"{SESSIONS['ledger-3'][0]}.response.md")
    assert "context/library/" in r3 and "ledger-1" in r3 and "ledger-2" in r3
    ok("ledger-3: the INV editor's reply cites the context/library/ entries ledger-1 and ledger-2")


if __name__ == "__main__":
    try:
        check_hashes()
        print("-- Level 1: task-level recursion (Propose -> Probe -> Compose), per task")
        for t in TASKS:
            check_level1(t)
        print("-- Level 2: harnessing-level recursion (reflect -> library -> next task)")
        check_level2()
    except AssertionError as exc:
        import traceback
        print(f"FAIL  check.py:{traceback.extract_tb(exc.__traceback__)[-1].lineno}  {exc}")
        raise SystemExit(1)
    print("All checks passed.")
