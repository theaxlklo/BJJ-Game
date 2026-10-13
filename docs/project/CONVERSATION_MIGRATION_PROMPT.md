# BJJ-Game — Conversation Migration Prompt

**Purpose:** A reusable, copy-paste starting message for a **new ChatGPT conversation** about the same BJJ-Game project. It is also a handoff checklist for a new Claude Code session. This file is a **handoff template, not a third living status document**. Do not keep manually changing SHA numbers or task status here: inspect the current repository at each migration.

**Repository:** https://github.com/theaxlklo/BJJ-Game

## How to migrate a ChatGPT conversation

1. Open this document from the [Project Hub](PROJECT_HUB.md) or GitHub.
2. Start a new ChatGPT conversation and **copy the text in the box below** as its first message. Optionally paste the most recent Claude Code handoff/report after it.
3. If ChatGPT can access GitHub through a connected app, use it. Otherwise share the current documentation links, or attach the relevant files. The prompt does not give a new conversation automatic access to prior private chats, local files, or machine state.
4. Ask for the next bounded task after the new assistant has checked the actual current source, ledger and SHA. The new chat should not edit GitHub merely because the handoff asks it to learn context.

## Copy into a new ChatGPT conversation

```text
We are continuing my BJJ-Game project from a previous ChatGPT conversation.

GitHub repository:
https://github.com/theaxlklo/BJJ-Game

Your first job is CONTEXT RECOVERY, not implementation. Read and reconcile the CURRENT main branch and the project's authoritative documentation before proposing or doing work.

Required reading order (use GitHub/connected sources or ask me for files only if you cannot access them):
1. AGENTS.md — current engineering invariants, local-first workflow, Ponytail Full, permanent Windows/Linux support, and multi-computer handoff.
2. CLAUDE.md — Claude Code's rules pointer, if giving Claude Code instructions.
3. docs/project/ENGINEERING_ROADMAP.md — current priorities and acceptance gates; beware older historical sections.
4. docs/project/OVERSIGHT_LEDGER.md — latest dated E-### entries; append, never rewrite earlier evidence.
5. docs/project/PROJECT_HUB.md and, optionally, PROJECT_HUB.html — searchable inventory of documents, agents, skills, and plugin/tool names.
6. Only the narrow feature spec and tests relevant to our NEXT actual task, e.g. GODOT_V1/docs/F1_MOUNT_PRACTICE.md for on-screen Mount practice. Do not read all historical files without a reason.

Important project decisions to preserve (verify current truth against main):
- One deterministic tactical Brazilian Jiu-Jitsu game, Godot 4.7.2 Standard / typed GDScript, with a frozen Python reference for ported mechanics. Do not rewrite or discard qualified engine work.
- One GitHub repo and ONE cross-platform Godot game: Windows and Linux/Omarchy are both permanent targets. I frequently switch computers. Windows is currently primary for hands-on development, but use whichever computer is actually active. Record tests separately for each OS; a pass on one does not imply a pass on the other. Never assume local paths, .venv, caches or uncommitted changes migrate automatically.
- The real Godot project already contains a 2D Mount practice scene, GODOT_V1/scenes/mount_practice.tscn, a graph-backed controller, Half Guard engine and related tests. Reuse actual implemented slices rather than starting over or inventing completed features.
- We use Claude Code with Ponytail Full; the repository contains four READ-ONLY reviewer agents, seven BJJ project skills, three reviewed third-party Claude skills and the named Ponytail plugin. Skills load on demand; plugin installation/enabled status is MACHINE-LOCAL. Consult PROJECT_HUB.md and AGENTS.md for the up-to-date inventory.
- The Windows Godot 4.7.2 Standard test_position_registry.gd has historically printed 'Position registry PASS: 431 assertions' but sometimes terminated with native 0xC0000005. Treat a nonzero exit as a FAIL even when PASS prints. Do not bypass teardown with OS.kill(), weaken the validator or claim a root cause without evidence. Prior Linux qualifications and the current Windows failure are NOT interchangeable; re-check the current ledger.
- Current near-term direction at the last handoff was to evaluate and improve ACTUAL F1 2D Mount practice playability, not restart the whole engine or enter another unlimited native-crash investigation. B2c Side Control implementation was not yet authorized/qualified at that checkpoint. The roadmap/ledger may have advanced since then — trust verified CURRENT repository state instead of these historical reminders.
- The authoritative roadmap/ledger are the ONLY two living progress documents. Historical proposals, frozen fixtures and prior PRs are preserved as evidence.
- Claude normally works local-first and commits/pushes only locally qualified, approved scope; new combat rules need explicit owner authorization. Do not force push, rewrite git history or silently change frozen oracle results. Do not issue tool calls that mutate GitHub merely to complete this context recovery.

Please do the following:
A. Verify the latest main SHA and date, recent ledger entry, current roadmap, and implemented vs proposed/blocked work. If you cannot access the repo, say so rather than inventing a state.
B. State the current Windows and Linux qualification separately (PASS / FAIL / BLOCKED / NOT TESTED), grounded in actual evidence.
C. Explain the available agent/skill/plugin workflow, without claiming the plugin is installed on this machine unless checked.
D. Tell me the smallest next actionable project step and what evidence it needs. If useful, provide a complete copyable Claude Code prompt (Ponytail Full, local-first, per-OS matrix) tailored to that step.
E. When I paste new Claude handoffs, compare their SHA/files/tests with actual evidence; update the roadmap/ledger when I authorize the work, preserving history.

Do not restart or redesign the game, duplicate an already implemented scene, initiate a massive refactor, or repeat a solved decision. If my newest pasted report conflicts with older status, investigate and report the difference.

OPTIONAL MOST RECENT HANDOFF / MY NEW REQUEST:
[Paste the latest Claude Code report, current local OS, or specific task here if available.]
```

## If starting a new Claude Code session instead

Open the **same existing repository** and begin with this short instruction, rather than pasting a long ChatGPT recap:

```text
Continue BJJ-Game from the current checked-out revision. Read AGENTS.md and CLAUDE.md first; then the latest ENGINEERING_ROADMAP.md and OVERSIGHT_LEDGER.md entries and only the relevant slice documentation. Follow Ponytail Full, the existing on-demand skills and read-only reviewer agents. At session start identify OS, branch, HEAD, working tree, pinned Godot executable/version and Python environment, and synchronize with origin/main only if safe. This is one Windows + Linux project; record platform qualification separately. Do not invent a new task, change rules or begin B2c without authorization. Report current status and the narrow next task before implementing. Existing F1 Mount practice and the known Windows headless registry crash are important historical context, but verify current ledger and test status rather than assuming they remain unchanged.
```

## Before switching computers or migrating again

- **Finish current work safely:** record branch, HEAD, status, task scope, exact test evidence and blockers in the latest handoff. Commit/push work that is qualified; a WIP branch can be pushed under an explicit unqualified label if the other computer needs it, never silently to qualified `main`.
- **On the next host:** verify local OS, dependencies and resources; fetch and fast-forward safely; do not assume local scratch experiments, WER dumps, active terminal sessions or plugin states traveled with Git.
- **When decisions change:** record the facts and owner approvals in `ENGINEERING_ROADMAP.md` and append a new `E-###` ledger entry. Update this template only if the permanent handoff policy changes.

**Navigation:** [Project Hub](PROJECT_HUB.md) · [Engineering Roadmap](ENGINEERING_ROADMAP.md) · [Oversight Ledger](OVERSIGHT_LEDGER.md) · [AGENTS.md](../../AGENTS.md) · [F1 practice](../../GODOT_V1/docs/F1_MOUNT_PRACTICE.md)
