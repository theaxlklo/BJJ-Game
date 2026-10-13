# Third-party Claude Code skills (reviewed 2026-10-13)

Vendored byte-for-byte into `.claude/skills/` after manual review. **No installer or package was executed**, and
no script, hook or dependency was vendored. Claude Code loads each skill only when its description matches the task.
`AGENTS.md` explains where each skill applies and which BJJ rules override it.

| Skill | Source (pinned commit) | License | Vendored files | Deliberately not vendored |
|---|---|---|---|---|
| `godot-gdscript` | gamedev-skills/awesome-gamedev-agent-skills@godot-gdscript, `0a70cfc64672d512c5b5b6006b5dcb5cf90dbdbd` | Apache-2.0 | `SKILL.md`, `references/annotations-and-typing.md` | none |
| `godot-ui-control` | gamedev-skills/awesome-gamedev-agent-skills@godot-ui-control, `0a70cfc64672d512c5b5b6006b5dcb5cf90dbdbd` | Apache-2.0 | `SKILL.md`, `references/layout-and-theming.md` | none |
| `systematic-debugging` | obra/superpowers@systematic-debugging, `bb92a77741419a4ab5f06e711a283343f1ada0c3` | MIT | `SKILL.md`, `root-cause-tracing.md`, `defense-in-depth.md`, `condition-based-waiting.md` | `find-polluter.sh` (npm-test bisector), `condition-based-waiting-example.ts`, authoring fixtures (`CREATION-LOG.md`, `test-*.md`) |

License texts: `LICENSE-awesome-gamedev-agent-skills-Apache-2.0`, `NOTICE-awesome-gamedev-agent-skills`, `LICENSE-superpowers-MIT` (this directory).

## Review findings

- **Godot 4.7.2:** both Godot skills target 4.7 / GDScript 2.0. Every runnable code sample (and the fragments, checked inside a function) parsed with `godot --headless --check-only` on 4.7.2.
- **Dangling references (intentional):** the skills mention `godot-nodes-scenes`, `godot-signals-groups`, `superpowers:test-driven-development`, `find-polluter.sh` and similar. These are not installed; do not install them without owner review.
- **BJJ conflicts handled in `AGENTS.md`, not by editing vendored files:** `godot-gdscript` teaches `_process(delta)`, `@export` tunables and `assert`; none may be used for authoritative simulation.
- **To update:** re-review the upstream diff, re-copy, and update the pinned commits above.
