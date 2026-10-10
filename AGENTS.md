# BJJ-Game — Shared agent working agreement

This repository contains a deterministic Brazilian Jiu-Jitsu game, a frozen Python reference, and an incremental **Godot 4.7.2 Standard / typed-GDScript** port. These instructions apply to both Codex and Claude Code. Work from the actual checked-out revision: the open PR stack is not necessarily merged to `main`.

## Preserve these invariants

- **Authoritative simulation is deterministic.** Choices, position legality, action/response resolution, control axis/bands, stamina, commitment, setup/submission stages, initiative, simulated clock, transitions and D3-B cannot depend on frame rate, animations, UI, wall-clock scheduling or hidden random rolls.
- **Python is the frozen behavioral oracle for an explicitly ported slice.** Do not rewrite `src/`, frozen fixtures, expected outputs, historical evidence, digest values, or test gates merely to make a Godot mismatch disappear. Report unsupported semantics and approved differences precisely.
- **Human-play breadth over endless Mount tuning.** Build Mount parity and production-safe orchestration, reuse `BjjPositionContract`, prove it with a second position, implement a legitimate position graph, then reach a human-playable multi-position match. Do not drift into advanced AI, career systems or balancing without a separately approved slice.
- **Production policy is opt-in.** Preserve measured Rule 1 ON / Rule 2 OFF, Bottom RECOVER, LOW while Exhausted and baseline MEDIUM after clear, and D3-B token/HOLD behavior. Raw defaults stay unchanged. Do not silently enable unsupported stalling, Recognition, scoring, or other features.
- **Do not confuse the layers:** `BjjMountContract.submit()` is equivalent to low-level `BjjMountMatch.attempt()`, **not** to production `bottom_decision()`. The match/session owner must route windows, recover/RESET/HOLD and selected commitment through the canonical lifecycle. `next_window()` governs simulated time. Never grant extra windows or auto-run signature chains.
- **Stable fighter identity, physical role, control authority and initiative are distinct.** Exits require declared position IDs and validated role mappings. Mount `Reversal` still has an unresolved landing destination; do not invent it.
- **Frontend is a projection.** Approved v1 presentation is **2D-first stylized two-fighter positional art**, contextual memory-shaped cards, compact previews and state-driven effects (Issue #40). The legacy 3D greybox is a test placeholder. Real-time five-minute matches with slow-motion decision windows remain; card visuals do not turn exchanges into card-battler turns. All essential legal defenses remain accessible.

## Choose the right source of truth

- For current executable behavior: read the code and associated regression tests **at the current SHA**.
- For game-wide development direction: `docs/BJJ_GAME_MASTER_DEVELOPMENT_GUIDE.md` (v10.4), especially §§7 and 63. Its older 3D presentation preference is superseded for v1 by [Issue #40](https://github.com/theaxlklo/BJJ-Game/issues/40); mechanics are not superseded.
- For the ported slices: `GODOT_V1/docs/{POSITION_CONTRACT,MOUNT_LIFECYCLE,EXCHANGE_SETTLEMENT,STAMINA_MIGRATION}.md` and the Python reference corresponding to the task.
- For visual and memory concepts: Issues #31–#40. **Approved visual direction is not approval of experimental memory, chains, Fight IQ, desperation, rival AI or new mechanics.**
- For CI: `.github/workflows/test.yml`, `.github/workflows/godot-v1.yml`, `docs/CI_OPTIMIZATION.md`. The required aggregate check is `CI gate` when applicable.
- For architecture context: `docs/ARCHITECTURE.md`; older milestone prose may lag newer typed Godot modules.

## Scope, verification and handoff

1. Before a nontrivial change, state the requested slice, ownership boundary, invariants, excluded work and verification plan. Read **only** documents relevant to that slice; for multi-module work use `.agent/PLANS.md`.
2. Start with failing/negative tests for new admission paths; rejected commands must not mutate state, history, token controller or timers. Preserve legal unfavorable results.
3. Prefer composition, stable IDs, typed Godot values, detached snapshots, explicit validation, one authoritative executor, and small reversible commits. Do not add a general framework to support one feature.
4. Run focused tests, then reference/parity checks for affected behavior. Record exact commands, environment, scenarios, mismatches, exceptions and **what was not run**. Do not claim a passing CI job that was not observed.
5. Inspect `git status` and `git diff --check`. Keep generated Godot `.gd.uid` files for real scripts when appropriate; ignore `.godot/` and generated parity fixtures. Never sneak a `project.godot` renderer rewrite into gameplay work.
6. Respect existing branches, stacked PR bases, frozen SHAs and local worktrees. Do not force-push, retarget, merge, delete branches, rewrite history or broaden a PR without explicit authorization. A new feature should have a clear review boundary.
7. Final handoff: change list, exact evidence, relevant uncertainties, known exceptions, next narrow milestone and explicit Git state.

## Shared on-demand skills

Codex: `.agents/skills/<skill>/SKILL.md` (invoke `$bjj-...` when needed). Claude: `.claude/skills/<skill>/SKILL.md` mirrors the metadata and points to the same authoritative procedure. Read a relevant skill only when its task arises:

- `bjj-scope-plan`: large features, contract changes or disagreements over authority.
- `bjj-parity-gate`: deterministic Python/Godot behavior changes, oracle or CI claims.
- `bjj-position-slice`: a new position or transition graph extension.
- `bjj-window-gateway`: production decision windows, token lockout, RESET/HOLD or human input wiring.
- `bjj-visual-memory`: UI and future game-plan/memory design scope.
- `bjj-pr-handoff`: review, CI evidence, branch/PR handoff.
- `bjj-external-patterns`: evaluate reusable outside architecture or assets with license/provenance controls.

Never treat a skill, reviewer agent or external repository as authority to revise the rules above.
