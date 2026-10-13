# Claude Code — B2a Side Control Specification + Integration Readiness

**Paste this entire prompt into a new Claude Code agent session opened at the BJJ-Game repository root.**

**Oversight documents:** This assignment is tracked by [`ENGINEERING_ROADMAP.md`](ENGINEERING_ROADMAP.md) and [`OVERSIGHT_LEDGER.md`](OVERSIGHT_LEDGER.md) in a separate, main-based documentation branch. They may not appear in the checked-out, unmerged PR #63 worktree. If absent locally, fetch and inspect `origin/docs/project-oversight-canonical:docs/project/` read-only; do not merge, rebase or cherry-pick the oversight branch into the gameplay stack merely to read it. Return an `OVERSIGHT HANDOFF` in the response; the project owner will direct subsequent ledger updates.

You are the lead engineer for a narrowly bounded **documentation-only** next slice of the BJJ tactical roguelike. The owner wants real positional breadth toward a complete playable match; avoid speculative overengineering and preserve deterministic engine behavior.

## Repository and verified starting state

Repository: `https://github.com/theaxlklo/BJJ-Game`

- Existing mainline draft stack: PR #17 through PR #63 (30 open PRs in one continuous ancestry chain, with gaps in PR numbers). **Not merged to `main`.**
- Parallel/differing early proposal: PR #44, **not an ancestor** of #63. Flag its disposition; **do not** blindly merge, close or retarget it.
- Latest expected docs PR: **#63**, branch `docs/match-incentives-heart-of-lion-spec`, exact head `650e7e1b9c6ba138a931c2805ce661e2268431b2`. Its GitHub workflow had **21/21 successful jobs** when last checked; reverify current state.
- #63 is based on #62, head `cd87bf21df16faf6ad859f579ee58d204618c5a6`. B1e introduced deterministic match-flow diagnostics and measurements, **not** new gameplay rules.
- Current functioning **opt-in** inter-position edge: Mount -> Half Guard. Half Guard Knee Slice -> Side Control is declared/producible but **blocked**, because Side Control has no receiver. There is no complete match from Standing, no full scoring, and F1 is Mount-only practice.

Start by running/recording current `git status --short`, branch, exact HEAD, remote and remote refs. Fetch as needed. Verify the expected PR #63 head and continuous ancestry before any edit. Do **not** discard existing worktrees, amend, force-push, rebase, reset, change existing PR bases, merge, or work directly on `main`. If the stack has moved or the worktree is dirty, preserve it, inspect and report; use a new safe worktree/branch only when appropriate. Do not pretend that the old SHA is current.

## Agent and skill orchestration (use the ACTUAL installed repo guidance)

First read `AGENTS.md`, `CLAUDE.md`, and `.agent/PLANS.md` (the latter if warranted by the cross-position scope). Read these Claude skill wrappers and their canonical instructions under `.agents/skills/`:

1. `.claude/skills/bjj-scope-plan/SKILL.md` — scope, ownership boundary and explicit exclusions.
2. `.claude/skills/bjj-position-slice/SKILL.md` — Side Control / graph architecture and validation.
3. `.claude/skills/bjj-pr-handoff/SKILL.md` — exact Git/PR/CI evidence, safe review handoff.
4. `.claude/skills/bjj-parity-gate/SKILL.md` — read for the **future independent oracle and negative-test plan**; do not run or modify existing parity corpora merely to write this spec.

Use **read-only** delegated reviewers in parallel when available, with strictly separated tasks:

- `pr-verifier`: audit branch ancestry, PR #44 divergence, #62/#63 heads, CI evidence, and safe later integration sequence. Return risk/issues only; **no edits**.
- `position-architect`: independently review the Half Guard -> Side Control proposed receiving boundary, fighter role mapping, authority/initiative, exit semantics and frozen Mount state. Return architecture issues, **no edits**.
- `replay-auditor`: examine the proposed verification matrix for deterministic replay, failure atomicity, missing rejection tests and oracle independence; **no edits**.

`design-sentinel` is **not** needed because this slice adds no artwork or UI. The lead agent alone owns file edits. If subagent tools are unavailable, execute the same independent reviews sequentially and disclose that in the handoff. Never ask subagents to edit or commit overlapping files.

## Scope A — Integration readiness, READ ONLY

Check and report, without modifying the existing stack:

- Actual `main` baseline, actual #63 branch/head, #62 relationship, ancestor consistency and whether PR #44 is superseded, conflicting or still useful as reference.
- Confirm exact-head CI status; distinguish successful CI, merged code and human-playable evidence.
- The bottom-up **recommended future** integration procedure for the large stack; call out conflicts, protections and rollback criteria. This is a *plan*, **not authorization to merge**.
- Any provenance/doc claims that differ from actual source or tests. Do not repair unrelated code/docs in B2a.

Do not get stuck collecting every historic log if the essential ancestry and current tip can be verified. The concrete next gameplay milestone is more important than another broad research investigation.

## Scope B — B2a Side Control rules + integration proposal, DOCUMENTATION ONLY

Study only relevant sources, especially:

- `docs/BJJ_GAME_MASTER_DEVELOPMENT_GUIDE.md` §§7, 9, 11, 14 and 63;
- `GODOT_V1/docs/{POSITION_CONTRACT,POSITION_GRAPH,POSITION_TOPOLOGY,HALF_GUARD_V0_RULES,HALF_GUARD_V0_ENGINE,MATCH_FLOW_DIAGNOSTICS}.md`;
- `GODOT_V1/scripts/positions/graph_match.gd` and the Half Guard catalog/resolver/match/gateway/edge code;
- existing independent Half Guard oracle and negative tests only insofar as needed to define the Side Control proof.

Write `GODOT_V1/docs/SIDE_CONTROL_V0_PROPOSAL.md` and, if needed, **only one brief link** in `GODOT_V1/docs/PORT_STATUS.md`. A proposal must distinguish **[CODE / observed]**, **[OWNER-APPROVED direction]**, **[PROPOSAL]**, **[OPEN owner decision]** and never silently promote a proposal into a frozen rule.

The document must cover:

1. **Purpose and slice boundaries:** a reachable Side Control after a *real* Half Guard Knee Slice, not a fabricated transition or forced progression. Inactive/default graph behavior and F1 stay unchanged.
2. **Identity and roles:** stable IDs, Side Control Top/Bottom, whether roles preserve from Half Guard, control authority, initiative on entry and response roles; Side Control owns a fresh position-local axis/bands rather than converting an overshoot from Half Guard.
3. **Minimal meaningful gameplay:** propose a BJJ-plausible small set of top/bottom legal techniques (eventual 3–5 per side) and corresponding defenses, with stable proposed action IDs; position-specific setup/readiness, commitment, stamina, legitimate submissions, feints only if justified. Avoid catalog sprawl.
4. **Explicit outcomes:** proposed exits and destinations (which are currently implemented, declared or absent), role-swapping semantics if any, and how an unsupported exit halts. No invented Mount Reversal landing or unauthorized automatic return route.
5. **Receiving seam and settlement:** how accepted Knee Slice -> Side Control is detected/classified/validated/committed, state continuity (fighter IDs, stamina current/max/latch, behavior-meter remainders, clock, global window IDs and events), inactive Half Guard state frozen, no bonus turn/clock advance/duplicate cost, receiver failure fail-closed after accepted exit.
6. **Standalone test-only Python oracle proposal**, independent of Godot and **not** altering frozen Mount Python production. Specify deterministic scenario grid, expected fixture flow, result-field comparisons and exact admission/rejection cases; do not create the oracle in B2a.
7. **Negative-first Godot test matrix:** invalid/unknown position and fighter, incorrect roles or initiative, wrong/stale window, invalid options/commitments/response, terminal or halted calls, rejection whole-state equality, repeated calls, deterministic double replay, real transition, unsupported exits, receiver construction failures, sealed/direct compatibility and graph history freeze.
8. **Separate question ledger:** bounded choices the owner must make before B2b's oracle and B2c's typed implementation. Offer clear alternatives with tradeoffs but no fabricated approved numbers.
9. **Implementation plan:** split future work into narrowly reviewable steps (owner approval -> oracle -> typed Side Control engine -> graph receiver -> tested mini-playable transition); include reasons to avoid a one-shot giant PR.

The new rule ideas in PR #63 (custom third-inactive-turn stalling, Momentum, once-per-match Heart of a Lion, REST and LOW zero-stamina fallback) are **documented only**. Do not implement, rebalance or silently apply them in B2a. Scoring, full Standing, new memory system, career, advanced AI, 2D visual overhaul and Mount retuning are also excluded.

## Scope C — verification and proposed PR

- B2a must be **docs-only**. Do not modify `.gd`, `.py`, `.uid`, frozen fixtures, or workflow files.
- Check links, consistency, Markdown formatting, `git diff --check` **after staging** as well as unstaged diff. Inspect every changed path against the intended base.
- Follow the repository's actual CI route. A documentation-only PR need not claim gameplay-parity tests were run. Report precisely what local and GitHub checks were observed vs skipped/not run.
- If the base SHA and repository permissions are valid, create a **new branch and DRAFT PR stacked on #63**, not on `main`; do not alter #63. Push normally, no force/amend, and reverify exact-head CI if it completes during this run. If publishing is unavailable, leave a prepared clean local commit and give commands and blockers; do not claim a PR was created.
- **Never** merge, mark ready, change existing PR bases or close #44. Stop at the B2a design-approval boundary.

## Mandatory final handoff for the project overseer (pasteable)

Conclude with this block, with real observations rather than predictions:

```
OVERSIGHT HANDOFF — B2a
Date:
Repository / working branch:
Base PR, base branch, exact base SHA:
Draft PR URL and number (or NOT CREATED):
Exact final head SHA:
Files changed (complete):
Implemented behavior: NONE — docs only
Specification delivered (key sections):
Current connected executable positions: Mount, Half Guard (opt-in) — verify if changed
CI exact SHA: PASS / FAIL / PENDING / NOT RUN; checked job counts:
Local checks (commands + outcomes):
Previously qualified tests/oracles affected: NONE / explain
Architecture/pr-verifier/replay-auditor findings (severity and actions):
PR #44 recommendation (no action taken):
Owner decisions required before coding (numbered, concise):
Residual risks/blockers:
Git state / confirmation no merges, retargets or force pushes:
Recommended exact next slice (B2b):
```

Be conservative: a passing CI run on a draft is **not merged**; a proposed ruleset is **not implemented**; an unsupported position exit is **not a win**. The project owner will review design choices before authorizing B2b mechanics.