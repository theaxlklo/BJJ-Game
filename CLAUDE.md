# Claude Code — BJJ-Game

Read and follow the repository-root `AGENTS.md`: it is the **shared production agreement** for Claude Code and Codex. Do not recreate or contradict it here.

- Start from the actual Git branch and scope. Read only the source-of-truth files relevant to the request.
- Project workflows are in `.claude/skills/` and their canonical instructions in `.agents/skills/`.
- Independent **read-only** reviewers live in `.claude/agents/`. Delegate bounded architecture/parity/design/PR review when useful; the main agent owns edits and integration. Do not make reviewers edit the same files.
- Large cross-module work uses `.agent/PLANS.md`. Ordinary fixes do not require a long plan.
- Ponytail Full is the default coding discipline; it never overrides `AGENTS.md` invariants, local tests or educational comments.
- Report verified tests vs inferred confidence. Under the local-first workflow in `AGENTS.md`, commit and push locally validated work to `main` without asking per push; new mechanics and open design decisions still need the owner.
