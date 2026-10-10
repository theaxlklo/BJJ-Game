---
name: bjj-pr-handoff
description: Audit BJJ-Game changes and prepare a safe stacked GitHub PR handoff with exact evidence and no unauthorized merges.
---

# bjj-pr-handoff

Use for review readiness, commit/PR description, CI interpretation or integrating a stacked branch.

1. Run `git status --short`, `git branch --show-current`, `git log -1 --oneline`, and inspect remotes/base. Confirm which open PR a change stacks on. Never assume `main` contains PR #30 or #39.
2. Check file diff against intended base, `git diff --check`, unexpected `.gd.uid`/`project.godot` changes, new dependencies, generated fixture files and evidence-only changes.
3. Classify with `.github/workflows/test.yml`/`tools/ci/route.py`; for Godot code require Godot parity, for Python/shared code expect its additional Python matrix. Read **exact run SHA** and `CI gate` rather than inferring from an earlier green PR.
4. Review authorization: no force push, merge, retarget, direct main, deleted branch or history rewrite without explicit permission. A PR description is not permission to merge.
5. Produce a compact handoff: purpose; base/head SHA; changed paths; frozen decisions preserved; exact local test commands/results; CI result or pending/unrun; approved exceptions; risks; next task. Flag every claim that is unverified.
