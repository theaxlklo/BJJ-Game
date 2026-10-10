# Agent skills index

The authoritative reusable BJJ-Game workflows are in `skills/*/SKILL.md` and are readable by Codex. Claude Code discovers small wrappers in `.claude/skills/` that reference these canonical files.

The project intentionally does **not** maintain a giant `SKILLS.md` or separate rulebook per tool. Always-on rules are in root `AGENTS.md`. Task-specific procedures are loaded only when relevant. See `docs/AGENT_WORKFLOW.md` for task routing and examples.
