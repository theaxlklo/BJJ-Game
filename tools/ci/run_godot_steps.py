"""Run every Godot qualification step from godot-v1.yml locally, in order, stopping at the first failure.

Local-first workflow: the workflow file stays the single list of steps, so a local run cannot drift from
the optional manual GitHub run. Steps that only exist on a CI runner (checkout, downloading Godot) are
skipped; GODOT_BIN (default ~/.local/bin/godot-bjj) is exposed to the steps as `godot` and this
interpreter as `python`. Needs PyYAML; this is a local convenience that CI never runs.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CI_ONLY = ('Checkout', 'Install pinned Godot')


def main():
    steps = yaml.safe_load((ROOT / '.github/workflows/godot-v1.yml').read_text())['jobs']['godot-v1']['steps']
    godot = os.environ.get('GODOT_BIN', str(Path.home() / '.local/bin/godot-bjj'))
    with tempfile.TemporaryDirectory() as shims:
        for name, target in (('godot', godot), ('python', sys.executable)):
            (Path(shims) / name).symlink_to(target)
        env = dict(os.environ, PATH=shims + os.pathsep + os.environ['PATH'])
        for step in steps:
            if 'run' not in step or step['name'].startswith(CI_ONLY):
                continue
            print(f'==> {step["name"]}', flush=True)
            # pipefail so `godot ... | tee` reports Godot's exit code, matching the workflow's own shells.
            if subprocess.run(['bash', '-e', '-o', 'pipefail', '-c', step['run']], cwd=ROOT, env=env).returncode:
                sys.exit(f'FAILED step: {step["name"]}')
    print('All Godot qualification steps passed.')


if __name__ == '__main__':
    main()
