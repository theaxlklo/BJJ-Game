# BJJ-Game — Shared agent working agreement

This repository contains a deterministic Brazilian Jiu-Jitsu game, a frozen Python reference, and an incremental **Godot 4.7.2 Standard / typed-GDScript** port. These instructions apply to both Codex and Claude Code. Work from the actual checked-out revision. Since 2026-10-13 `main` contains the whole integrated development stack through PR #66 and is the working branch (see *Local-first workflow*).

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
- For optional manual qualification: `.github/workflows/test.yml` (manual dispatch only), `.github/workflows/godot-v1.yml`, `docs/CI_OPTIMIZATION.md`. Automatic GitHub Actions are disabled; local test results are the gate.
- For progress and open decisions: `docs/project/ENGINEERING_ROADMAP.md` and `docs/project/OVERSIGHT_LEDGER.md` (the only living progress documents).
- For a quick, non-authoritative inventory of project documents, Claude reviewer agents, skills and the named Ponytail plugin: `docs/project/PROJECT_HUB.md` (also has a searchable HTML view). For a new ChatGPT conversation or Claude session, use the reusable handoff template `docs/project/CONVERSATION_MIGRATION_PROMPT.md` (not an authoritative progress document).
- For architecture context: `docs/ARCHITECTURE.md`; older milestone prose may lag newer typed Godot modules.

## Local-first workflow (owner decision 2026-10-13; supersedes the earlier PR/CI process)

- **Primary assistant:** Claude Code with Ponytail Full (smallest complete change). Ponytail never overrides the invariants above, the local tests, or the educational comments.
- **Work directly on `main`.** No PRs for ordinary development. Refactor existing code when needed to meet approved engineering requirements, keeping deterministic behavior and pinned parity counts unchanged.
- **New machine:** `python3 tools/setup_dev.py` checks the setup read-only (see `docs/DEV_SETUP.md`); `--install` offers safe installs after confirmation. Run `tools/ci/run_godot_steps.py` with the interpreter that has PyYAML (the project `.venv` if the checker created one).
- **Test locally before every push:** Godot 4.7.2 headless (`GODOT_BIN`, default `~/.local/bin/godot-bjj`) and system `python3`. `python3 tools/ci/run_godot_steps.py` runs every step of `godot-v1.yml` (needs PyYAML); `PYTHONPATH=src python3 -m unittest discover -s tests` runs the Python suite for Python/shared changes; `python3 -m unittest discover -s tools/ci` covers the CI tooling. Run what the touched paths require and report what was not run.
- **Native Windows** is supported for the same commands: use the project `.venv\Scripts\python.exe` instead of `python3`, set `GODOT_BIN` to the Godot `*_console.exe` (the plain `.exe` prints nothing headless), and keep Git for Windows installed because the workflow steps run under Git Bash, never the WSL launcher. `tools/setup_dev.py` prints the exact Windows download, checksum and `setx` command.
- **Commit and push locally validated work straight to `origin/main`.** No separate permission per commit or push inside an approved task. Report the SHA, commands and results; the owner has ChatGPT review GitHub afterwards.
- **GitHub Actions are manual only** (`workflow_dispatch`); use them for optional full qualification, e.g. `gh workflow run test.yml --ref main -f target_sha="$(git rev-parse HEAD)" -f full_qualification=true`.
- **Still needs owner approval:** new gameplay mechanics and unresolved design decisions (for example SC-D1–SC-D15 and B2a.1). Never invent or silently change rules. Force-pushes, history rewrites, branch deletion and closing historical PRs also need explicit authorization.
- **Comments:** follow *Educational code comments* below.
- **Skills:** use the existing BJJ skills first. Evaluate skills.sh additions selectively; do not install unreviewed skills.
- **Living documents:** keep progress in `docs/project/ENGINEERING_ROADMAP.md` and `docs/project/OVERSIGHT_LEDGER.md`; technical specifications stay where they are.

## Permanent Windows + Linux support (owner decision 2026-10-13)

- **Single project:** Maintain one Godot 4.7.2 Standard PC game, one Python behavioral reference, and one repository for Windows and Linux. Windows is the primary hands-on development environment, but Linux is a first-class continuously supported target, never a later separate port. Keep match authority, assets, gameplay data and test fixtures shared; isolate true OS-specific setup, launch, filesystem, input and packaging differences.
- **Both-platform verification:** For runtime or UI work, separately record Windows and Linux engine/build, resource import, actual interactive launch and keyboard/mouse focus where possible, focused headless tests with exact PASS markers **and process exit 0**, relevant Python/Godot parity, and exports when applicable. If a host cannot be accessed, mark NOT TESTED, and don't claim dual-platform-ready. One platform passing never overrides a failure on the other. Docs-only work doesn't require invented executable evidence.
- **Deterministic portability:** Render timing, UI, input, operating system and packaging must not affect legal actions, decision windows, stamina, clock, replay, or frozen oracles. Check case-sensitive resource paths, separators, line endings and platform-specific environment assumptions.
- **Windows qualification blocker stays visible:** The pinned 4.7.2 Standard test_position_registry.gd script intermittently exits 0xC0000005 after printing 431 PASS assertions. That marker does not make a crashing process PASS. Never suppress this gate, weaken its validator or adopt OS.kill() as a teardown bypass. Keep the native investigation bounded while unrelated verified on-screen 2D playability can advance; B2c's full Windows qualification remains BLOCKED.
- **Reuse F1:** The existing GODOT_V1/scenes/mount_practice.tscn and graph-backed controller are the initial interactive 2D surface. Do not create a parallel scene, fork for Linux, or claim this is already a complete scored match.
- **Permanent documentation:** Every substantive handoff records each platform's PASS / FAIL / NOT TESTED / BLOCKED status, exact evidence and next gate in docs/project/ENGINEERING_ROADMAP.md and docs/project/OVERSIGHT_LEDGER.md. Technical instructions stay in their subsystem docs.

## Multi-computer development (owner decision 2026-10-13)

The owner alternates between Windows and Linux/Omarchy computers on this same repository. Everything below applies on top of *Permanent Windows + Linux support*, which stays the source for the single-project rule, per-platform evidence and the Windows blocker.

- **Start of every session:** identify the current operating system, branch, `HEAD`, working-tree status, Godot executable and version (`GODOT_BIN`), and the available Python environment, before reading or changing anything. Do not assume this machine looks like the previous one.
- **Synchronize safely:** inspect `git status` for uncommitted or untracked work first. When the tree is safe, update with `git pull --ff-only origin main`. Never discard local changes, force-push or rewrite history to synchronize; if a fast-forward is impossible, stop and report.
- **Before switching machines:** commit and push work that is locally qualified. Preserve unfinished or unqualified work on a clearly named temporary branch (not `main`) and say that it is unqualified, so it is never mistaken for qualified work.
- **Nothing local is shared:** never assume absolute paths, `.godot/` caches, `.venv` environments, downloaded tools (including Godot) or uncommitted files exist on the other machine; detect and use what is present here.
- **Portability:** keep the `.gitattributes` LF rules for `.gd` and `.py`, and check path-sensitive code and resource filename capitalization when touching files (Linux is case-sensitive).
- **Qualification is per operating system:** record Windows and Linux results separately; a PASS on one never establishes a PASS on the other. Until it is actually executed on Linux, the registry test and the rest of the Godot qualification are **NOT TESTED** there, while on Windows the position-registry crash remains **BLOCKED/FAIL** as described above.

## Educational code comments (permanent rule)

Write code so the project owner can understand and learn from it later. The codebase should teach how the BJJ game works without costing maintainability or Ponytail's lean principles.

- Explain **why** complex logic exists, not what each line does. Cover non-obvious algorithms, calculations, stamina mechanics, initiative decisions, position transitions and deterministic-simulation rules.
- Document important constraints, edge cases and design tradeoffs. Where a simpler-looking implementation would violate an invariant (determinism, atomic rejection, frozen Python parity, a single settlement path), say why the existing approach is necessary.
- Give significant public functions a brief comment on purpose, inputs, outputs and side effects when these aren't obvious.
- Prefer clear names and small functions to excessive comments. No obvious comments, long tutorials in source files or redundant explanations. Match the file's existing idiom (plain `#` comments in GDScript, docstrings in Python).
- Keep comments accurate: update them whenever you change the code they describe.
- Applies to new and meaningfully modified code only. Do not launch a repository-wide comment rewrite.

## Scope, verification and handoff

1. Before a nontrivial change, state the requested slice, ownership boundary, invariants, excluded work and verification plan. Read **only** documents relevant to that slice; for multi-module work use `.agent/PLANS.md`.
2. Start with failing/negative tests for new admission paths; rejected commands must not mutate state, history, token controller or timers. Preserve legal unfavorable results.
3. Prefer composition, stable IDs, typed Godot values, detached snapshots, explicit validation, one authoritative executor, and small reversible commits. Do not add a general framework to support one feature.
4. Run focused tests, then reference/parity checks for affected behavior. Record exact commands, environment, scenarios, mismatches, exceptions and **what was not run**. Do not claim a test or job that was not run and observed.
5. Inspect `git status` and `git diff --check`. Keep generated Godot `.gd.uid` files for real scripts when appropriate; ignore `.godot/` and generated parity fixtures. Never sneak a `project.godot` renderer rewrite into gameplay work.
6. Respect existing branches, frozen SHAs and local worktrees. Do not force-push, rewrite history, delete branches or close historical PRs without explicit owner authorization. Keep each commit a clear, reviewable boundary.
7. Final handoff: change list, exact evidence, relevant uncertainties, known exceptions, next narrow milestone and explicit Git state.

## Shared on-demand skills

Codex: `.agents/skills/<skill>/SKILL.md` (invoke `$bjj-...` when needed). Claude: `.claude/skills/<skill>/SKILL.md` mirrors the metadata and points to the same authoritative procedure. Read a relevant skill only when its task arises:

- `bjj-scope-plan`: large features, contract changes or disagreements over authority.
- `bjj-parity-gate`: deterministic Python/Godot behavior changes, oracle or CI claims.
- `bjj-position-slice`: a new position or transition graph extension.
- `bjj-window-gateway`: production decision windows, token lockout, RESET/HOLD or human input wiring.
- `bjj-visual-memory`: UI and future game-plan/memory design scope.
- `bjj-pr-handoff`: legacy PR/CI handoff procedure; no longer required (use the local-first workflow above).
- `bjj-external-patterns`: evaluate reusable outside architecture or assets with license/provenance controls.

### Third-party skills (Claude Code only; reviewed 2026-10-13, pinned in `docs/third_party/skills/PROVENANCE.md`)

Load each only when its task arises; the BJJ rules above always override them, and the BJJ skills come first.

- `godot-gdscript`: general GDScript 4.x idiom (typing, lifecycle, signals, `await`). Never apply its frame-driven patterns to authoritative simulation: no `_process`/`delta` timing, no `@export` gameplay constants, and no `assert` for invariants (a production `assert` only aborts the running function and a test can still print PASS), so use explicit validation that returns an error.
- `godot-ui-control`: Control, Container, Theme and focus layout, for the 2D presentation shell (F1) only. `bjj-visual-memory` still governs design scope; keep the projection-only rule and 1366x768 accessibility.
- `systematic-debugging`: root cause before fixes, for real bugs, failing tests and parity mismatches (not routine edits). It agrees with "report mismatches, never silently fix" and negative-first tests. Its references to uninstalled skills (`superpowers:*`, `godot-nodes-scenes`, ...) and the missing `find-polluter.sh` are intentional; install nothing further from those collections without owner review.

Never treat a skill, reviewer agent or external repository as authority to revise the rules above.
