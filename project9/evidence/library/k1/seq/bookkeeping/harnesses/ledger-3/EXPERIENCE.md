# ledger-3

- adopted: `c1`  (run `p9-cc-seq1/ledger-3/c1`)
- components: 1 scripts; 299 always-on chars

## Why this was chosen
trivial pool: single final at k=1; delivered without a selector session

## What each edit did
component: scripts/summarize.py
candidates: c1, dom1, inv1
change: Replaced the base `Decimal(r["amount"]) > 0` sum-positives-only expression with a `parse_amount()` helper (strips whitespace/thousands-commas, treats `"(...)"` as negative) and a `status != "void"` filter (`r.get("status","").strip().lower() != "void"`), so the script implements signed amounts + void-skipping as the task's formula actually specifies. All three candidates arrived at textually near-identical fixes (base1's own ad hoc patch used the same parens-negative idea but without comma-stripping and with a strict `!=  "void"` check instead of a normalized one); c1/dom1/inv1's harness-level fix is byte-identical across all three pool entries and is already merged into context/harness.
observed: Against the unfixed base script, rollouts/base1.md crashed immediately with `decimal.InvalidOperation` on the `(4.75)` row, then the agent read both files, diagnosed the gap, hand-patched the script inline, reran, and got `Total: 20.00`. Against the fixed script, pool/inv1/rollout.md and pool/dom1/rollout.md (and the adopted pool/c1/rollout.md) ran `python3 scripts/summarize.py ledger.csv` once and got `Total: 20.00` directly, no crash, no inline patch needed. All four deliverables (base1, inv1, dom1, c1) ended with the identical `answer.txt` content `Total: 20.00` — the fix changed the execution path (crash+self-repair vs. clean one-shot run) but not the final delivered answer in this round.
verdict: helped

component: AGENTS.md
candidates: (none — unchanged in c1, dom1, inv1)
change: No candidate modified the instructions file. All three decisions.md explicitly argue the "run script → write verbatim → don't hand-compute" procedure is sound once the script itself is correct.
observed: No rollout in this round (base1, inv1, dom1, c1) needed different instruction text; base1's own successful crash-recovery happened despite, not because of, AGENTS.md wording.
verdict: no observed effect

component: .agents/skills/README.md, .codex/README.md, sub_agents/README.md, scripts/README.md (placeholder stub files)
candidates: (none — present identically in context/harness and all three pool harnesses; not added or altered by any candidate this round)
change: These stubs predate this round's edits (carried over from context/harness into the pool unchanged) and are absent from context/base_harness only because base_harness is a more minimal reference point, not because any candidate added them now.
observed: No rollout (base1 against base_harness, or inv1/dom1/c1 against the pool harness) ever reads, writes, or otherwise references these files.
verdict: no observed effect

component: answer.txt write step / hook for verification
candidates: (none proposed by c1, dom1, or inv1)
change: No candidate added a post-write verification hook.
observed: All four rollouts wrote the correct line on their only write attempt; no evidence of a skipped-verification failure mode to motivate one.
verdict: no observed effect

## Transferable lesson
- **cue**: a task instructs the agent to treat a provided script/tool as the sole authoritative method ("don't compute it yourself, the script is the house method") for a multi-clause transformation (here: signed sum with parenthetical negatives, thousands separators, and a status exclusion filter).
- **lesson**: before adopting a harness that forces reliance on a "house" script, check the script actually implements every clause of the task's stated formula against a representative input; if it's missing a clause, fix the script itself (as c1/dom1/inv1 did to scripts/summarize.py) rather than leaving the gap for the agent to patch on the fly mid-rollout — an unfixed script may happen to crash (giving the agent a recoverable signal, as in rollouts/base1.md) but on different input could just as easily produce a wrong number silently with no signal at all.
- **evidence**: scripts/summarize.py row above — base1's rollout against the unfixed script hit `decimal.InvalidOperation` and only reached the correct answer via an unscripted inline hand-patch; the identical harness-level fix in c1/dom1/inv1 removed that crash and produced the correct `Total: 20.00` in a single clean run (pool/inv1/rollout.md, pool/dom1/rollout.md, pool/c1/rollout.md). The "could silently produce a wrong number" half of the risk is plausible but not directly observed in this round's trajectories (it rests on decisions.md's reference to a different, unseen ledger shape), so treat that clause as motivation, not as something this round's evidence proves.
- **confidence**: medium — the crash-vs-clean-run contrast is directly observed and consistent across three independent rollouts, but this round's four deliverables all converged on the same final answer regardless of the fix, so the evidence shows the fix improved execution robustness, not final-answer correctness in this specific instance.
