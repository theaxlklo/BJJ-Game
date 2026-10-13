# BJJ-Game — Project Hub & Document Catalog

**Inventory snapshot:** 2026-10-13 · **Repository:** [theaxlklo/BJJ-Game](https://github.com/theaxlklo/BJJ-Game) · **Scope:** Git-tracked project documentation and tools. This is a **navigation/catalog page, not a third living progress ledger**; actual decisions and milestones remain in the roadmap and oversight ledger.

> **Start here:** [Engineering Roadmap](ENGINEERING_ROADMAP.md) → [Oversight Ledger](OVERSIGHT_LEDGER.md) → [Master Development Guide](../BJJ_GAME_MASTER_DEVELOPMENT_GUIDE.md) → [Current F1 Mount Practice](../../GODOT_V1/docs/F1_MOUNT_PRACTICE.md).
>
> **Searchable overview:** [PROJECT_HUB.html](PROJECT_HUB.html). Open the HTML file locally in a browser for a searchable catalog of 140 document/text files. No dependencies or login are required for the dashboard itself; document links open GitHub.

## Current development in one glance

| Item | Current reference or boundary |
|---|---|
| Game | One BJJ-Game, same Godot 4.7.2 Standard and typed GDScript on Windows and Linux |
| Primary assistant | Claude Code + **Ponytail Full** (project workflow) |
| Optional assistant | Codex CLI / Codex reading the shared `AGENTS.md`; availability differs per machine |
| Repository policy | [AGENTS.md](../../AGENTS.md), [CLAUDE.md](../../CLAUDE.md) |
| Current work | Existing graph-backed [F1 2D Mount Practice](../../GODOT_V1/docs/F1_MOUNT_PRACTICE.md); **do not build a duplicate** |
| Windows qualification | Position registry prints 431 PASS assertions but intermittently exits `0xC0000005`; **BLOCKED/FAIL** |
| Linux qualification | **NOT TESTED for this crash checkpoint**; historical Linux CI isn't current machine evidence |
| Source of truth | [Roadmap](ENGINEERING_ROADMAP.md) and [Ledger](OVERSIGHT_LEDGER.md), only two living progress documents |

## Agents — four defined, read-only Claude reviewers

Claude's main agent owns edits. These four reviewer definitions **exist in the repository**; they are not necessarily running in every session.

| Agent | Purpose | Mode |
|---|---|---|
| [`design-sentinel`](../../.claude/agents/design-sentinel.md) | 2D interface, accessibility and memory-card design review | Read-only; invoked when relevant |
| [`position-architect`](../../.claude/agents/position-architect.md) | PositionContract, fighter identity, roles, initiative and graph transitions | Read-only; invoked when relevant |
| [`replay-auditor`](../../.claude/agents/replay-auditor.md) | Deterministic replay, Python↔Godot parity and negative-case test review | Read-only; invoked when relevant |
| [`pr-verifier`](../../.claude/agents/pr-verifier.md) | Git/CI and historical PR audit (legacy PR-focused reviewer) | Read-only; invoked when relevant |

Source: [Claude reviewer folder](../../.claude/agents/) and [agent workflow](../AGENT_WORKFLOW.md).

## Shared BJJ skills — seven defined

The canonical instructions are in `.agents/skills/`; Claude discovers wrappers under `.claude/skills/`. Skills are **on-demand procedures**, not background workers or separate plugins.

| Skill | Purpose | Usage |
|---|---|---|
| [`bjj-scope-plan`](../../.agents/skills/bjj-scope-plan/SKILL.md) | Bounded cross-module planning and approved scope | On demand |
| [`bjj-parity-gate`](../../.agents/skills/bjj-parity-gate/SKILL.md) | Deterministic replay, frozen reference and rejection tests | On demand |
| [`bjj-position-slice`](../../.agents/skills/bjj-position-slice/SKILL.md) | New positional engine and graph transitions | On demand |
| [`bjj-window-gateway`](../../.agents/skills/bjj-window-gateway/SKILL.md) | Real production windows, initiative and D3-B routing | On demand |
| [`bjj-visual-memory`](../../.agents/skills/bjj-visual-memory/SKILL.md) | 2D scene, HUD, memory presentation without invented mechanics | On demand |
| [`bjj-external-patterns`](../../.agents/skills/bjj-external-patterns/SKILL.md) | Review outside code, licenses, inspirations and provenance | On demand |
| [`bjj-pr-handoff`](../../.agents/skills/bjj-pr-handoff/SKILL.md) | Historical stacked-PR handoff; legacy, not normal local-first workflow | Legacy / occasional |

## Reviewed third-party skills — three vendored

| Skill | Purpose | Usage |
|---|---|---|
| [`godot-gdscript`](../../.claude/skills/godot-gdscript/SKILL.md) | Godot 4.x syntax and idioms, under BJJ deterministic constraints | On demand, vendored/reviewed |
| [`godot-ui-control`](../../.claude/skills/godot-ui-control/SKILL.md) | Godot Control nodes, accessibility, layout and focus | On demand, vendored/reviewed |
| [`systematic-debugging`](../../.claude/skills/systematic-debugging/SKILL.md) | Root-cause investigations; use only for actual defects | On demand, vendored/reviewed |

Sources and licenses: [Third-party skill provenance](../third_party/skills/PROVENANCE.md). The vendor docs mention some other skills, but those **are not installed or approved** merely because they are mentioned.

## Plugins & development tools

| Type | Name | Verified project role / installation status |
|---|---|---|
| Claude Code plugin | **`ponytail@ponytail`** | Primary workflow uses *Ponytail Full*. [setup_dev.py](../../tools/setup_dev.py) checks whether the plugin is installed and enabled **on the current machine**. Git alone cannot guarantee machine installation. |
| Assistant | **Claude Code** | Primary local-first assistant. Use [AGENTS.md](../../AGENTS.md) and [CLAUDE.md](../../CLAUDE.md). |
| Assistant (optional) | **Codex CLI** | Can use `AGENTS.md` and shared skills; not a required Claude plugin, not assumed installed. |
| Game runtime | **Godot 4.7.2 Standard** | Both Windows and Linux target the same project and pinned engine version. |
| Tests/tooling | **Python and PyYAML** | Python frozen behavioral reference; PyYAML required by [run_godot_steps.py](../../tools/ci/run_godot_steps.py). |
| Sync | **Git + GitHub** | One remote repository; fast-forward safe pull, qualified work to `main`. GitHub Actions manual-only. |

**Not a repository plugin inventory:** ChatGPT plugins/connectors and machine-local Claude Code plugin installations are not stored in the tracked repo. To discover the *current computer's* actual plugin state, run `claude plugin list` or `python3 tools/setup_dev.py` (on Windows, use the local Python command). Do not mislabel vendored skills as installed Claude plugins.

## All tracked documents, grouped by function

This catalog displays **140 Markdown/text files** from `docs/`, `GODOT_V1/docs/`, and repository README files. Screenshots, compressed fixtures and other non-document evidence are intentionally excluded from the searchable file list.

| Document family | Files | Navigate |
|---|---:|---|
| **Current roadmap & ledger** | 2 | [Browse/search in HTML](PROJECT_HUB.html) |
| **Getting started & operations** | 6 | [Browse/search in HTML](PROJECT_HUB.html) |
| **Game design & historical concept** | 2 | [Browse/search in HTML](PROJECT_HUB.html) |
| **Godot implementation & position specs** | 24 | [Browse/search in HTML](PROJECT_HUB.html) |
| **Tooling references & provenance** | 1 | [Browse/search in HTML](PROJECT_HUB.html) |
| **Playtest records** | 13 | [Browse/search in HTML](PROJECT_HUB.html) |
| **Frozen evidence & data** | 2 | [Browse/search in HTML](PROJECT_HUB.html) |
| **Historical Mount research & gates** | 50 | [Browse/search in HTML](PROJECT_HUB.html) |
| **Historical stamina, recovery & research** | 36 | [Browse/search in HTML](PROJECT_HUB.html) |
| **Other reference & past planning** | 4 | [Browse/search in HTML](PROJECT_HUB.html) |

### How to find what you need

- **Current decisions and next milestones:** the Roadmap, then E-### entries in the Ledger.
- **Rules and conceptual design:** Master Development Guide, position rules sheets and proposals in `GODOT_V1/docs/`.
- **Actually implemented behavior:** source code and tests at the checked-out Git SHA; `PORT_STATUS.md` and F1 documentation are helpful orientation, but may include older historical sections.
- **Coding assistants:** `AGENTS.md` → `docs/AGENT_WORKFLOW.md` → specific reviewer/skill `SKILL.md`.
- **Old measurements:** `docs/MOUNT_*`, `docs/STAMINA_*`, `docs/HANDOFF_*`, `docs/BURST_*`, and `docs/evidence/`. Keep frozen evidence intact.

### Naming convention (without breaking links)

Use a readable navigation title instead of moving, bulk-renaming or deleting historical files. Future *new* documents should make their authority and scope explicit: `[FEATURE]_PROPOSAL.md`, `[FEATURE]_RULES.md`, `[FEATURE]_ENGINE.md`, `[FEATURE]_TEST_REPORT.md`. The two living progress files keep their established names. Archived evidence retains its existing names and frozen content. No historical claims are retroactively rewritten.

**Maintenance:** When adding/removing project agents, shared skills, reviewed skills or plugins, update this hub. Continue recording actual work/progress **only** in the Roadmap and Oversight Ledger. The HTML is a convenient catalog snapshot, not a source for gameplay decisions.
