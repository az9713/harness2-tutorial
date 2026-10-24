# Harness² tutorial

A self-contained study guide for **Harness²: Recursive Agent Harnessing for an Open World** (Xu et al., Northwestern University and Google Cloud AI Research, arXiv:2610.14224v1, 9 Oct 2026).

**Live page:** https://az9713.github.io/harness2-tutorial/

## What the page covers

- A 15-minute core: the seven ideas of the paper.
- The eight harness components (C1–C8) and the order an editor must use to place a fix.
- Task-level recursion: one Propose–Probe–Compose step, with the paper's JobBench example (43.1 → 77.8).
- Parallel and sequential recursion, with the run count per budget k (4k executor runs, 3k improver sessions).
- Harnessing-level recursion: the Experience Reflector and the per-domain library.
- Main results, ablations, failure cases and limits.
- The claims of the explainer video, checked against the paper.
- The code release: file map, commands and warnings.
- How to apply the method to a Claude Code harness.
- A 16-question self-test.

The **Theory** tab describes Harness² with theoretical computer science: a formal model (harness space, the step Φ as a Markov kernel, the two recursion levels as a fold), verification limits (indistinguishability, identifiability, the optimizer's curse), the logic of enforcement (safety and liveness, execution monitors, edit automata), learning without labels (regret, the adaptivity gap), and a cost model for the eight components. Every statement carries a tag: Paper, Code, Literature or Model.

Three animated figures step through the recursion: the two loops over a task stream (Fig. B), the JobBench example (Fig. C), and the run plan for k = 1–5 in parallel or sequential mode (Fig. D).

## Project ideas

[`harness2-projects.html`](https://az9713.github.io/harness2-tutorial/harness2-projects.html) describes 10 projects that apply the Harness² method to a Claude Code setup: a hook compiler, a reflector hook with an experience library, a `/harness-step` skill, an always-on context auditor, a blind best-of-k selector, a skill A/B bench, an independent checker library, evolve-strong/deploy-cheap transfer, an adapter for the released code, and a domain harness for a repeated pipeline. Each has a diagram that maps it onto the Harness² stages, a file tree, snippets, cost, evidence and risks.

## Resources

| Resource | Link |
|---|---|
| Paper (arXiv) | https://arxiv.org/pdf/2610.14224 |
| Code (GitHub) | https://github.com/google-research/harness2 |
| Project site | https://harness2.github.io/ |
| Explainer video (YouTube) | https://www.youtube.com/watch?v=pW2ktrJlsyE&t=566s |

Every number on the page cites a table, figure or prompt in the paper, or a file in the code release. The paper and the video are not copied into this repository; follow the links above.

## View it locally

Open `harness2-learn.html` in a browser. The page is one file. The Theory tab loads MathJax 3.2.2 from the jsDelivr CDN, so its math needs network access; the Tutorial tab works offline.
