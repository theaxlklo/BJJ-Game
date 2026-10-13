---
name: bjj-external-patterns
description: Evaluate Slay the Spire 2, GrappleMap or other external implementations as architectural references with legal and gameplay isolation.
---

# bjj-external-patterns

Use for reusing third-party ideas/code/data, reading an external repository or proposing a new dependency.

1. Establish source URL, revision, *actual provenance* (official vs community/decompiled/reverse-engineered), license for code/data/assets separately and what is unknown. A GitHub repo's public visibility is **not** source-code permission.
2. Isolate the generic architectural insight: canonical immutable definitions vs mutable state, command/result boundaries, read-only view-models, deterministic replay, presentation/state separation, content IDs, reusable pose references.
3. Assess whether the BJJ engine already implements the idea (`BjjMountCatalog` + match state + PositionContract). Choose no-op, adapt the pattern in original code, or propose a future licensed experiment. Never bulk-copy decompiled Slay the Spire 2 code or assets.
4. For GrappleMap, separate public-domain pose data and provenance from third-party meshes; its schematic keyframes are references, not accurate gripping simulation or legally authoritative transitions.
5. Prove any candidate with one bounded local example and failure modes. No new dependency, mechanics, CI burden or renderer change without an approved milestone and measurable benefit.
6. Report provenance, licenses, copy/reimplementation decision, tradeoffs and explicit non-adopted items.
