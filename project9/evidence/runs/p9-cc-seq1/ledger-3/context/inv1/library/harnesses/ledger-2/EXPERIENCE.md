# ledger-2

- adopted: `c1`  (run `p9-cc-seq1/ledger-2/c1`)
- components: 1 scripts; 299 always-on chars

## Why this was chosen
trivial pool: single final at k=1; delivered without a selector session

## What each edit did
component: scripts/summarize.py (core fix: comma-stripping, parentheses-as-negative parsing, status!=void filter)
candidates: c1, dom1, inv1 (all inherited; none of this round's edits introduced it — it was already present in `context/harness`, the round's starting point, per decisions/c1.md item 1 describing an earlier merge of inv1+dom1 fixes)
change: replaces base_harness's broken one-liner (`sum(Decimal(r["amount"]) for r in rows if Decimal(r["amount"]) > 0)`, which crashes on `"1,250.00"` and silently drops negative/parenthetical rows) with a `parse_amount` helper plus a `status != "void"` filter.
observed: context/rollouts/base1.md (run against unfixed base_harness) crashes with `decimal.InvalidOperation` on row `"1,250.00"`, forcing the agent to hand-diagnose and hand-patch the script mid-rollout to reach `Total: 912.00`. All three pool rollouts (c1.md, dom1.md, inv1.md), running against the pre-fixed script, either get `Total: 912.00` straight from the script (dom1, inv1) or never even need to run it because the answer is obviously right by inspection (c1). No pool rollout hits the crash or the silent-wrong-answer path.
verdict: helped — but this is evidence from a prior round's edit baked into the starting harness, not something any candidate in *this* pool contributed.

component: scripts/summarize.py — status-lookup safety (`r.get("status", "")` vs `r["status"]`)
candidates: dom1 (changed `.get("status", "")` to `r["status"]`, removing the safe default)
change: drops the dict `.get` default, so a row missing a `status` key would now raise `KeyError` instead of being treated as not-void.
observed: context/pool/dom1/rollout.md still prints `Total: 912.00` — the actual `ledger.csv` always has a `status` column, so the removed default is never exercised either way.
verdict: no observed effect

component: scripts/summarize.py — parse_amount restructuring (flag variable vs early-return form)
candidates: inv1 (rewrote the `negative`-flag version into an equivalent early-return version, renamed `raw`→`s`)
change: purely stylistic restructuring of the same parsing logic (strip, replace commas, detect `(...)`, negate).
observed: context/pool/inv1/rollout.md runs the script and gets `Total: 912.00`, identical to dom1's and the unmodified version's output — no behavioral difference on any tested input.
verdict: no observed effect

component: scripts/summarize.py — c1 (no change)
candidates: c1
change: none — c1's harness.diff is empty; byte-identical to `context/harness`.
observed: c1's rollout (context/rollouts/c1.md) never runs the script at all. It reads `ledger.csv` directly and hand-computes 1250.00 − 300.50 − 49.50 + 12.00 = 912.00, violating AGENTS.md step 3 ("Do not compute the total yourself. The script is the house method"). It reaches the same numeric answer only because this ledger is small enough to eyeball correctly; nothing in the harness enforced or even detected the bypass.
verdict: confounded — the correct output says nothing about whether the harness's instruction-following guarantee holds; a single rollout is the only evidence, and the one real risk this run exposed (procedure bypass) didn't affect the final artifact, which is why both "fixed" and "unchanged" harnesses looked identical at selection time.

component: .agents/skills/README.md, .codex/README.md, sub_agents/README.md, scripts/README.md (extension-point placeholder stubs)
candidates: c1, dom1, inv1 (identical across all three, inherited unchanged from context/harness)
change: none this round — stub files describing unused extension mechanisms (skills, codex hooks, sub-agents).
observed: no rollout in base1, c1, dom1, or inv1 ever references a skill, hook, or sub-agent.
verdict: no observed effect

component: AGENTS.md
candidates: c1, dom1, inv1 (unchanged across all, including base_harness)
change: none
observed: identical instructions followed (or, in c1's case, silently bypassed) across all rollouts; no candidate proposed touching it.
verdict: no observed effect

## Transferable lesson
- **cue**: a task harness hands the agent a small deterministic "house method" script to run over tabular/financial data, and the task statement's own formula (signed amounts, parenthetical negatives, exclusion filters) is more complete than what the shipped script implements.
- **lesson**: when AGENTS.md instructs the agent to trust a script's output rather than compute the value itself, verify the script actually implements every clause of the task's stated formula (sign conventions, exclusion filters, locale-style number formatting like thousands separators) by running it against the real input file before trusting the instruction layer — a broken script under a "don't compute it yourself" instruction produces silent wrong answers on inputs that don't happen to crash it, and the fix belongs in the script (scripts/summarize.py), not in the instruction text (AGENTS.md).
- **evidence**: base1 (context/rollouts/base1.md) crashed on the unfixed script and hand-patched it correctly to 912.00 — demonstrating the base script's formula gap was real, not hypothetical, on this exact input. The fixed script (inherited by all three pool candidates) then let dom1 and inv1 reach the correct total by just running it, with no crash and no hand computation. Both of this round's incremental edits to the fix (dom1's `.get` removal, inv1's restructuring) produced no observed behavioral difference, so they don't add to this lesson's evidence. c1 made no edit and happened to bypass the script entirely via mental math, which is a separate, unconfirmed risk (see c1 row) and is excluded from this lesson's evidential basis.
- **confidence**: medium — the crash-and-correct-hand-patch in base1 is direct, concrete evidence that script-formula gaps are the real failure mode in this task family; the "fix belongs in the script" direction is corroborated by two independent prior-round candidates (inv1, dom1) converging on the same fix with no rollout ever needing an AGENTS.md change. Confidence isn't high because this round itself contributed no new contrastive evidence — the fix predates the pool, and the pool's own edits (dom1, inv1 tweaks) were both no-observed-effect.
