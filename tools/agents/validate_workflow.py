"""Standard-library consistency check for the shared BJJ-Game agent workflow.

Usage: python tools/agents/validate_workflow.py
Does not execute untrusted skills, mutate files, require Godot, or contact the network.
"""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
CANON = ROOT / '.agents' / 'skills'
CLAUDE = ROOT / '.claude' / 'skills'
errors = []
required = ['AGENTS.md', 'CLAUDE.md', '.agent/PLANS.md', 'docs/AGENT_WORKFLOW.md']
for path in required:
    if not (ROOT / path).is_file():
        errors.append(f'missing {path}')
canonical = {p.parent.name: p for p in CANON.glob('*/SKILL.md')}
wrappers = {p.parent.name: p for p in CLAUDE.glob('*/SKILL.md')}
if not canonical:
    errors.append('no canonical skills found')
if canonical.keys() != wrappers.keys():
    errors.append(f'skill mismatch: canonical={sorted(canonical)}, claude={sorted(wrappers)}')
for name, path in canonical.items():
    for label, candidate in [('canonical',path), ('Claude',wrappers.get(name))]:
        if not candidate:
            continue
        content = candidate.read_text(encoding='utf-8')
        match = re.match(r'\A---\n(.*?)\n---\n', content, re.DOTALL)
        if not match:
            errors.append(f'{label} {name}: missing frontmatter')
            continue
        block = match.group(1)
        if f'name: {name}' not in block:
            errors.append(f'{label} {name}: name mismatch')
        if not re.search(r'^description: \S+', block, re.MULTILINE):
            errors.append(f'{label} {name}: missing description')
        if label == 'Claude' and f'.agents/skills/{name}/SKILL.md' not in content:
            errors.append(f'Claude {name}: missing canonical reference')
for path in (ROOT / '.claude' / 'agents').glob('*.md'):
    txt = path.read_text(encoding='utf-8')
    if not txt.startswith('---\n') or '\nmodel: inherit\n' not in txt:
        errors.append(f'{path.name}: unexpected agent frontmatter')
if errors:
    print('Agent workflow check FAILED')
    for error in errors:
        print(' -', error)
    sys.exit(1)
print(f'Agent workflow check PASS: {len(canonical)} canonical skills, '
      f'{len(wrappers)} Claude wrappers, '
      f'{len(list((ROOT / ".claude" / "agents").glob("*.md")))} read-only reviewers')
