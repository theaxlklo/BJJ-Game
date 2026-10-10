---
name: bjj-position-slice
description: Implement or review a new deterministic BJJ position using the universal PositionContract and validated position transitions.
---

# bjj-position-slice

Use when adding Side Control, Standing, Guard, Back Control or position-graph transitions. Read `AGENTS.md`, Master Guide §§7, 9, 11, 63, `GODOT_V1/docs/POSITION_CONTRACT.md` and current Mount adapter; only deepen research for the actual position.

1. Specify a position ID, two stable fighter IDs, role mapping, named control authority and initiative. The signed axis is a **position-local contest**, not universally vertical top/bottom.
2. State legal actions and responses (stable IDs), commitment options, setup and applicable submission routes, drift and outcome/exit mapping. Start with the smallest playable proof; the guide's eventual 3–5 actions/side target is not a reason to skip correctness.
3. Compose a position-specific resolver/state behind `BjjPositionContract`; no cloned `MountMatch` with string switches or global rule tables masquerading as reuse.
4. On a transition, validate destination is declared/implemented, create the receiving position with legal state, preserve stable identities and correctly map physical roles. Exit labels are **not** instantiated destinations. Leave unresolved Mount Reversal unresolved.
5. Negative tests: invalid actions/responses/roles, nonfinite axes, rejected mutation, terminal submissions, role change, missing destinations, determinism, compatible setup/submission stage.
6. Preserve existing Mount oracle and contract tests; report whether this second position demonstrates actual reuse or still needs a graph owner. Do not silently add new combat rules to the Python frozen source.
