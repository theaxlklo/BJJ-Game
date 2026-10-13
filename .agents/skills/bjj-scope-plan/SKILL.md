---
name: bjj-scope-plan
description: Plan a bounded BJJ-Game engine or design change without altering frozen rules or expanding the approved milestone.
---

# bjj-scope-plan

Use for a cross-module proposal, new capability, contract revision or disagreement about implementation authority. Do not use for tiny self-contained fixes.

1. Inspect the checked-out SHA/branch and only the relevant files. Treat stacked PRs as real dependencies, not as merged history.
2. State: user goal; current implemented behavior; approved design decision; desired diff; excluded functionality; files touched; owner/controller; and tests to preserve.
3. Identify the one authoritative command path and which part merely reads/presents it. Separate engine invariants, session deadlines, UI affordances and hypothetical mechanics.
4. Propose the smallest reversible implementation with stable IDs and validation. Do not introduce a generalized framework without proof from a second use case.
5. If there is a missing rule (e.g. Mount Reversal destination), identify a decision gate rather than fabricating gameplay.
6. Output a compact scope contract, negative-first acceptance tests and the subsequent verification skill to run. For large changes, use `.agent/PLANS.md`.

References: `AGENTS.md`, Master Guide §§7/63, relevant Godot slice documents, and the exact code/tests.
