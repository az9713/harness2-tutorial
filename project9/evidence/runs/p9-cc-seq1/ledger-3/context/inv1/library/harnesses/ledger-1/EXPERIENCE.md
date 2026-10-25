# ledger-1

- adopted: `c1`  (run `p9-cc-seq1/ledger-1/c1`)
- components: 1 scripts; 299 always-on chars

## Why this was chosen
trivial pool: single final at k=1; delivered without a selector session

## What each edit did
component: scripts/summarize.py
candidates: c1, dom1, inv1 (identical fix in all three)
change: Replaced `total = sum(Decimal(r["amount"]) for r in rows if Decimal(r["amount"]) > 0)` with a version that (1) adds `parse_amount()` to strip `(...)` wrappers and negate the value, (2) sums every row's signed amount instead of discarding negatives, and (3) skips rows whose `status` (trimmed, lowercased) equals `void`.
observed: context/rollouts/base1.md (old script) runs `python3 scripts/summarize.py ledger.csv` on 100.25/-20.10/5.00 and gets `Total: 105.25` — the agent follows AGENTS.md's "don't compute it yourself" instruction and writes that wrong value verbatim to answer.txt (context/deliverables/base1/answer.txt). All three pool rollouts (context/pool/c1/rollout.md, pool/dom1/rollout.md, pool/inv1/rollout.md), run against the identical fixed script, get `Total: 85.15` and write it verbatim (context/deliverables/{c1,dom1,inv1}/answer.txt), matching the task's own definition (100.25 − 20.10 + 5.00 = 85.15).
verdict: helped
component: AGENTS.md
candidates: c1, dom1, inv1 (all left unchanged from base_harness)
change: none — all three decisions.md explicitly chose to keep the "run the script, don't hand-compute, write it verbatim" procedure once the script was correct.
observed: no execution difference attributable to this file; base1 and the pool rollouts all follow the same AGENTS.md text, and the only output difference traces to the script's output, not to any instruction change.
verdict: no observed effect
component: .agents/skills/README.md, .codex/README.md, sub_agents/README.md, scripts/README.md
candidates: c1, dom1, inv1 (identical placeholder stubs added in all three, absent from base_harness)
change: added empty scaffold placeholders (editing-lever comments only: "add one as sub_agents/<name>/AGENT.md...", "add ONE file .codex/hooks.json...", etc.) with no actual skill, subagent, or hook content.
observed: no rollout invokes or references any skill/subagent/hook; all three pool rollouts and the final harness rollout proceed identically through "run script → write answer.txt" with no mention of these files.
verdict: no observed effect

## Transferable lesson
- **cue**: a harness instructs the agent to trust and transcribe the output of an owned deterministic script ("don't compute it yourself, the script is the house method"), and the task spec states a formula (signed sum, parenthetical negatives, status-based exclusion) that the script is supposed to implement.
- **lesson**: before trusting an instruction that tells the agent to defer to a script, read the script itself against the task's own stated formula line-by-line (every clause: sign handling, notation variants, filter conditions) — a script that passes on the one sample input can still silently drop or mis-handle cases (negative rows, parenthetical notation, excluded statuses) that the sample doesn't exercise, and the fix belongs in the script, not in the instruction telling the agent to trust it.
- **evidence**: scripts/summarize.py row above — base_harness's script implemented only the "sum positive amounts" fragment of the task formula and dropped negatives entirely with no void-skip or parens handling; base1's rollout (trusting the unfixed script) produced a wrong, deterministic `105.25` on every run, while the fixed script (identical across all three pool candidates) produced the correct `85.15`.
- **confidence**: high — the contrast is a direct before/after on the same script and same ledger input (base1 vs. the three pool rollouts), isolating the one component that changed, with no other file differing between the wrong-answer and right-answer runs.
