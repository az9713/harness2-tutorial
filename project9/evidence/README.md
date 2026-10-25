# Project 9 run evidence

This folder holds the smallest set of output files of one live Project 9 run that shows both recursions of Harness². `check.py` tests each claim against these files. It makes no model calls and costs nothing.

## The run

- Command: `python run.py` in WSL (sequential mode, k = 1, library on, 3 tasks: `ledger-1`, `ledger-2`, `ledger-3`).
- Time: 2026-10-24. The first output file was written at 21:26 and the last at 21:46, local time. Git does not keep file times.
- Executor: Claude Code `claude -p`, model `claude-haiku-4-5-20251001`, 12 task runs.
- Editors and reflector: Claude Code `claude -p`, model alias `sonnet`, 12 sessions.
- Login: the Claude subscription. Every task-run log shows `"apiKeySource": "none"`.
- Cost reported by the CLI at API prices: $3.31 for the 12 sessions, $0.42 for the 12 task runs, $3.73 in total. The subscription paid for it.

The replay page `harness2-p9-run.html` uses a different, 1-task run (`--tasks 1`). This folder is the 3-task run, because only a run with 2 or more tasks can show the library going to a later task.

## How to check

Run this from the repository root:

```
python project9/evidence/check.py
```

The script needs `project9/h0/` (the base harness H₀) next to this folder. It prints one `PASS` line for each check, and a `NOTE` line for each fact that is not a pass condition. It stops with exit code 1 at the first failed check.

To test the hashes only, run `sha256sum -c SHA256SUMS` in this folder. `SHA256SUMS` covers the 113 data files. It does not cover `README.md`, `check.py`, `.gitattributes` or itself.

## What the checks show

### Level 1: task-level recursion, inside one task

For each of the 3 tasks:

1. **H₀ runs first.** `runs/p9-cc-seq1/<task>/harnesses/base/` is equal to `project9/h0/`. Run `base1` used it.
2. **Propose.** Two editor sessions (`inv1`, dimension INV, and `dom1`, dimension DOM) each wrote a new harness. `harnesses/inv1/` and `harnesses/dom1/` are different from H₀. Each session's `audit/*.response.md` holds the notes in `summary.json`, and each `audit/*.meta.json` holds the same cost.
3. **Probe.** The runs `inv1` and `dom1` ran the two new harnesses. Each run's log (`stream.jsonl`) shows its first `python3 scripts/summarize.py ledger.csv` call. That call printed the same last line that the run's harness script prints when `check.py` runs it again.
4. **Compose.** The session `c1` merged the two harnesses into `harnesses/c1/`. Run `c1` used it.
5. **Select.** `summary.json` shows that Select chose `c1`. With k = 1 there is only one final, so no selector session ran.
6. **Run count.** `summary.json` shows R = 4 task runs and P = 3 editor sessions, the planned numbers for k = 1.
7. **Result.** On `ledger-1`, H₀'s script prints `Total: 105.25` and the c1 script prints `Total: 85.15`, the correct total. `base1` scored 0 and `c1` scored 1.

### Level 2: harnessing-level recursion, across tasks

1. **Reflect.** After each task, the reflector session wrote one lesson. The lesson in `summary.json` is in `library/k1/seq/bookkeeping/harnesses/<task>/EXPERIENCE.md`, and in the reflector's `audit/experience.*.response.md`.
2. **Store.** The library entry `harnesses/<task>/harness/` is equal to that task's `c1` harness.
3. **The next task reads the library.** The INV editor's context for `ledger-2` held the entry `ledger-1`. For `ledger-3`, it held `ledger-1` and `ledger-2`. These copies (`runs/p9-cc-seq1/<task>/context/inv1/library/`) are byte-equal to the library entries. The `ledger-1` editor had no library, because no task came before it.
4. **The editors used it.** The `ledger-2` INV editor's reply cites `library/harnesses/ledger-1/EXPERIENCE.md`. The `ledger-3` INV editor's reply cites the `context/library/` entries `ledger-1` and `ledger-2`.
5. **Each task restarts from H₀.** `base1` of `ledger-2` and `ledger-3` used H₀, not the `c1` harness of the task before. The library is the only thing that goes to the next task.

## What the checks do not show

- **The files cannot prove that they are authentic.** Anyone can edit a file before a commit. The hashes show only that the files did not change after this commit. The time of the commit on GitHub is the anchor. `check.py` shows that the files agree with each other, and that the harness scripts give the same output again without a model.
- **Session ids.** Only the 12 task-run logs record a `session_id`. The editor and reflector sessions record their label, model alias, cost and reply. They do not record a session id: the harness2 audit file `meta.json` has no field for it. Nobody outside the account can look up a session id.
- **Model runs do not repeat exactly.** A new live run gives different text, and its scores can be different.
- **The base scores of `ledger-2` and `ledger-3` do not measure H₀.** In both tasks, run `base1` edited `scripts/summarize.py` during the run (the Edit tool) and then wrote the correct total. H₀'s script stops with `decimal.InvalidOperation` on these ledgers.
- **Run `c1` of `ledger-2` did not call the script.** It read the ledger and wrote the total itself. So the Probe check of step 3 links the run to its harness only for the other 11 runs.
- **The library did not change a score.** A control run with the library off (`--no-library`) gave the same 6 scores. That run is not in this folder.

## Which files are here, and which are not

Each path here is the path in the run folder: `<repo>/project9/runs/live/X` is `project9/evidence/X`.

| Path | Files | Content |
|---|---|---|
| `live.log` | 1 | The console output of the run |
| `runs/scores.json` | 1 | The 6 scores |
| `runs/p9-cc-agg1/<task>/summary.json` | 3 | harness2's record of each task: stages, notes, costs, ledger, selection, lesson |
| `runs/p9-cc-seq1/<task>/harnesses/{base,inv1,dom1,c1}/` | 24 | `AGENTS.md` and `scripts/summarize.py` of each harness, before its run |
| `runs/p9-cc-seq1/<task>/context/inv1/library/` | 11 | The library as the INV editor saw it (`ledger-2`, `ledger-3`) |
| `executions/p9-cc-agg1/<task>/base1/`, `executions/p9-cc-seq1/<task>/{inv1,dom1,c1}/` | 27 | `stream.jsonl` (the full Claude Code log), `workspace/answer.txt`, and `workspace/ledger.csv` for `base1` |
| `audit/` | 36 | `meta.json`, `mission.md` (the prompt) and `response.md` (the reply) of the 12 sessions |
| `library/k1/seq/bookkeeping/` | 10 | The library after the run: `INDEX.md` and 3 entries |

Files of the run that are not here:

- **9 sessions in `audit/` from 21:48 to 22:03.** An early `--no-library` run used the same output folder and added them. That run reused the cached results of this run, so it is not valid evidence. `check.py` names the 12 sessions of this run. Each one's reply matches a stage note in `summary.json`.
- **The scripts in each run's `workspace/`.** They show the state after the run. `base1` of `ledger-2` and `ledger-3` changed them. The `harnesses/` copies show the state before the run.
- **The editors' working copies** (`audit/*.workspace/`), the composer's pool and the reflector's inputs (`context/c1/pool/`, `reflection/`), and lock files. They repeat the files above.

## Changes to the files

The files are copies of the run output with these text replacements, applied in this order. Nothing else changed. The hashes were made after the replacements.

| Replaced | With | Count |
|---|---|---|
| `/mnt/c/Users/<user>/Downloads/harness2_PE` (the local repository path) | `<repo>` | 161 |
| `-mnt-c-Users-<user>-Downloads-harness2-PE` (the same path as a folder name) | `<repo-slug>` | 12 |
| `/home/<user>` (the WSL home folder) | `<home>` | 12 |
| the local user names, as whole words (in `ls -la` output) | `<user>` | 136 |
