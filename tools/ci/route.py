"""Conservative qualification routing. No dependencies or gameplay imports."""
import json
import os
import re
import subprocess
from pathlib import Path, PurePosixPath

SHA = re.compile(r'[0-9a-f]{40}')
# Historical tests read reports outside docs/evidence; these are shared inputs.
SHARED_DOC_MARKERS = (
    'MASTER_DEVELOPMENT_GUIDE', 'POLICY', 'SEMANTICS', 'FREEZE', 'EVIDENCE',
    'DEFINITION_OF_DONE', 'MEASUREMENT', 'PREREGISTRATION', 'VERIFICATION',
    'CHARACTERIZATION', 'DISTRIBUTIONS', 'AMENDMENT', 'INVARIANT', 'RESULT',
    'DOD', 'MOUNT_', 'STAMINA_', 'HANDOFF_', 'BURST_', 'R1_', 'SETUP_',
    'ARCHITECTURE', 'NAMING_LOCK',
)


def path_category(path):
    if not isinstance(path, str) or not path or path.startswith('/') or '\\' in path or any(ord(c) < 32 for c in path) or '..' in path.split('/'):
        return 'UNKNOWN'
    if path.startswith(('.github/', 'tools/ci/')):
        return 'CI_INFRASTRUCTURE'
    if path.startswith(('docs/evidence/', 'src/', 'tests/')) or path in ('pyproject.toml', 'setup.py', 'setup.cfg', 'requirements.txt', 'uv.lock', 'poetry.lock'):
        return 'PYTHON_OR_SHARED'
    if path.startswith('docs/') and any(token in PurePosixPath(path).name.upper() for token in SHARED_DOC_MARKERS):
        return 'PYTHON_OR_SHARED'
    if path == 'README.md' or (path.startswith(('docs/', 'GODOT_V1/docs/')) and path.endswith('.md')):
        return 'DOCUMENTATION_ONLY'
    if path.startswith('GODOT_V1/'):
        return 'GODOT_ONLY'
    return 'UNKNOWN'


def classify(paths):
    categories = {path_category(path) for path in paths} or {'UNKNOWN'}
    category = next(item for item in ('UNKNOWN', 'CI_INFRASTRUCTURE', 'PYTHON_OR_SHARED', 'GODOT_ONLY', 'DOCUMENTATION_ONLY') if item in categories)
    full = category in ('UNKNOWN', 'CI_INFRASTRUCTURE', 'PYTHON_OR_SHARED')
    return dict(category=category, python_required=full, godot_required=full or category == 'GODOT_ONLY', reason='path categories: ' + ', '.join(sorted(categories)))


def plan(paths, event, ref, full=False):
    result = classify(paths)
    if full or (event == 'push' and ref == 'refs/heads/main') or event not in ('push', 'pull_request', 'workflow_dispatch'):
        result.update(python_required=True, godot_required=True, reason=result['reason'] + '; full event/explicit qualification')
    return result


def changed_paths(base, head, triple, directory='.'):
    if not all(SHA.fullmatch(value or '') and value != '0' * 40 for value in (base, head)):
        raise ValueError('missing or invalid diff SHA')
    span = base + ('...' if triple else '..') + head
    data = subprocess.check_output(['git', '-C', directory, 'diff', '--name-status', '-z', '--find-renames', span])
    fields = data.decode('utf-8', errors='strict').split('\0')
    paths = []
    index = 0
    while index < len(fields) - 1:
        status = fields[index]; index += 1
        if not re.fullmatch(r'(?:[AMDTUXB]|[RC][0-9]+)', status):
            raise ValueError('unrecognized diff status: ' + status)
        count = 2 if status.startswith(('R', 'C')) else 1
        for _ in range(count):
            if index >= len(fields) - 1 or not fields[index]:
                raise ValueError('truncated diff record')
            paths.append(fields[index]); index += 1
    return paths


def main():
    event = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
    name = os.environ['GITHUB_EVENT_NAME']
    head = event.get('pull_request', {}).get('head', {}).get('sha') if name == 'pull_request' else os.environ['GITHUB_SHA']
    actual = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    if not SHA.fullmatch(head or '') or actual != head:
        raise SystemExit('checkout is not the intended event head')
    inputs = event.get('inputs', {})
    if name == 'workflow_dispatch' and inputs.get('target_sha') != head:
        raise SystemExit('target_sha must equal the selected branch SHA at dispatch time')
    base = event.get('pull_request', {}).get('base', {}).get('sha') if name == 'pull_request' else event.get('before')
    span = ''
    try:
        paths = changed_paths(base, head, name == 'pull_request')
        span = base + ('...' if name == 'pull_request' else '..') + head
        error = ''
    except (ValueError, subprocess.CalledProcessError, UnicodeError) as exc:
        paths = []
        error = '; diff unavailable: ' + str(exc)
    result = plan(paths, name, os.environ.get('GITHUB_REF', ''), inputs.get('full_qualification') in (True, 'true'))
    result['reason'] += error
    print(json.dumps(dict(head=head, paths=paths, **result), indent=2))
    with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
        for key, value in result.items():
            output.write(f'{key}={str(value).lower() if isinstance(value, bool) else value}\n')
        output.write(f'target_sha={head}\n')
        output.write(f'diff_span={span}\n')


if __name__ == '__main__':
    main()
