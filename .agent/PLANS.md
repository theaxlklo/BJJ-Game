# Lightweight execution plans for cross-module BJJ-Game work

Use this file for an architectural change spanning multiple runtime modules, a new position, a position-graph or save-schema change, or a production policy change. Do **not** require it for a typo, small test fix or docs-only update.

Maintain a short working plan in your task notes (create an issue-scoped planning document only if asked), using:

1. **Baseline:** current branch/HEAD, stacked PR dependency, observed tests and docs.
2. **Scope:** expected behavior, precise owner, in-scope files and exclusions.
3. **Contracts:** stable IDs, fighter roles, initiative, clock, rejection order, null/terminal behavior, transition targets and failure atomicity.
4. **Proof:** negative-first cases, deterministic traces/oracle, relevant native tests and CI route.
5. **Steps:** smallest coherent implementation/verification checkpoints, rollback path.
6. **Review:** actual file diff, parity results, limitations, follow-up decisions that need the owner.

If the source and design disagree, record the disagreement. Never invent numerical outcomes to make a plan feel complete. Keep the plan current; don't confuse the plan with proof of execution.
