---
name: bjj-parity-gate
description: Verify deterministic Python-to-Godot behavior, regression evidence and negative-first admission for a changed BJJ engine slice.
---

# bjj-parity-gate

Use when changing Godot engine behavior, Python parity fixtures, native contract code, or claiming oracle equivalence.

1. Record current SHA, Godot `4.7.2.stable` runtime and touched owner. Identify the relevant **unchanged Python reference** and its independently generated scenario file.
2. Add negative-first tests: invalid/wrong role and initiative, missing/invalid IDs, terminal state, repeated call, exhaustion/cost boundaries and non-mutation of histories/token/clock. Only include cases relevant to the slice.
3. Import the project headlessly. Run the applicable native tests. Generate Python fixtures *using the existing generators*, then run matching `*_reference.gd` tests (see `docs/AGENT_WORKFLOW.md`). Never edit expected output to silence a mismatch.
4. Respect approved historical exceptions with their explicit provenance; report exclusions by count and cause. **No novel exclusion** without owner review.
5. Preserve replay determinism (identical command/event sequence must reproduce all state and history). Check `git diff --check`; include actual shell exit codes/log filtering specified by the CI workflow.
6. Report exact scenario/operation/comparison/mismatch counts, tested Python/Godot versions, failures, CI vs local, and **not run**. If a test isn't available or can't be run, say so—do not infer success.

CI authority: `.github/workflows/godot-v1.yml`, `.github/workflows/test.yml`. The aggregate CI gate, when required, is authoritative only for its exact event head.
