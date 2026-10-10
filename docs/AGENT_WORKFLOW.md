# Coding-agent production workflow

This is a **workflow reference**, not a new game design or policy amendment. Repo-wide rules are in `AGENTS.md`. Claude additionally reads `CLAUDE.md`; Codex natively reads `AGENTS.md`.

## One shared skill library

`.agents/skills/*/SKILL.md` contains the authoritative procedures. `.claude/skills/*/SKILL.md` contains tiny launchers pointing to those procedures, to avoid divergent duplicated copies. Claude's independent reviewer configurations live in `.claude/agents/`. Codex uses the shared skills and can perform the same reviewer roles when asked explicitly (no special runtime plugin needed).

### Suggested workflows

| Task | Lead workflow | Independent check | Evidence |
|---|---|---|---|
| Mount/gameplay compatibility | `bjj-scope-plan` + `bjj-parity-gate` | replay auditor | Python oracle, negative admission, Godot replay |
| Match gateway / human commands | `bjj-window-gateway` | replay auditor + architect | production D3-B/window parity and non-mutation |
| New position | `bjj-position-slice` | position architect | standalone typed tests, graph/role transition proof |
| Visual shell / memory cards | `bjj-visual-memory` | design sentinel | non-authoritative snapshots and accessible 1366x768 UI |
| PR readiness | `bjj-pr-handoff` | PR verifier | SHA/base, diff, CI gate, explicit limitations |
| Outside design / StS2 / GrappleMap | `bjj-external-patterns` | architect + design sentinel | license/provenance, self-authored abstraction only |

One lead owns a change. Reviewers **report** issues, not competing modifications. A skill is a playbook, not a free-standing automation or permission to merge.

## Local verification examples (from repo root)

Use `GODOT_BIN` for the pinned **4.7.2 Standard** executable (`~/.local/bin/godot-bjj` on the Omarchy laptop; unset `DRI_PRIME` if needed). Only run suites relevant to touched paths. Capture actual return codes with `set -o pipefail` before `tee`.

```bash
GODOT_BIN="${GODOT_BIN:-$HOME/.local/bin/godot-bjj}"
"$GODOT_BIN" --headless --path GODOT_V1 --editor --import --quit
"$GODOT_BIN" --headless --path GODOT_V1 --script res://tests/test_position_contract_boundaries.gd
PYTHONPATH=src python GODOT_V1/tests/generate_exchange_reference.py
"$GODOT_BIN" --headless --path GODOT_V1 --script res://tests/test_position_contract_reference.gd
PYTHONPATH=src python GODOT_V1/tests/generate_d3b_reference.py
"$GODOT_BIN" --headless --path GODOT_V1 --script res://tests/test_d3b_boundaries.gd
"$GODOT_BIN" --headless --path GODOT_V1 --script res://tests/test_d3b_reference.gd
```

For Python/shared code, CI routing and historical invariants, consult `.github/workflows/test.yml` instead of inferring a successful shortcut. Some existing native negative tests intentionally produce specific engine errors, so follow the workflow's exact log assertions rather than globally demanding zero `ERROR` lines.

## Source and decision precedence

- Current source/tests and frozen qualification establish **implemented behavior**.
- Master Guide v10.4 establishes broad architecture; Issue #40 establishes later **2D-first presentation** direction only.
- Ideas in Issues #31–#38 are backlog research; none silently authorizes changing Mount, knowledge gates, turn/window semantics or AI.
- PR #39 PositionContract remains a low-level exchange adapter; production Bottom decisions must still call `bottom_decision()`.
- The published open PR stack is not automatically on `main`. Identify the current checkout and PR base before claiming a feature exists on main.

## Sample task request

"On the current worktree, use `bjj-window-gateway`. Implement only a match-level gateway over existing MountMatch and PositionContract; do not change Python mechanics. Begin with non-mutation tests for stale, duplicate, wrong-fighter, terminal and D3-B lockout requests. Run the required Godot reference tests; report exact evidence and leave GitHub unchanged."
