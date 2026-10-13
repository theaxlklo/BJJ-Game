"""Run every Godot qualification step from godot-v1.yml locally, in order, stopping at the first failure.

Local-first workflow: the workflow file stays the single list of steps, so a local run cannot drift from
the optional manual GitHub run. Steps that only exist on a CI runner (checkout, downloading Godot) are
skipped; GODOT_BIN (default ~/.local/bin/godot-bjj, with an .exe suffix on Windows) is exposed to the steps as
`godot` and this interpreter as `python`. Needs PyYAML; this is a local convenience that CI never runs.

Windows: the steps are bash scripts, so they run under Git for Windows' bash (never the WSL launcher), and the
`godot`/`python` shims are tiny sh wrappers because creating symlinks on Windows needs special privileges.
The steps hard-code /tmp for logs, which Git Bash maps to its own temp folder while native Windows Python reads
it as a tmp folder at the root of the current drive, so on Windows /tmp/ is rewritten to a per-run scratch folder both agree on.
Point GODOT_BIN at the Godot *_console.exe; the plain .exe is a GUI program whose headless output is lost.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

from godot_runner_support import default_godot, find_bash, make_shim, step_script

ROOT = Path(__file__).resolve().parents[2]
CI_ONLY = ('Checkout', 'Install pinned Godot')


def main():
    steps = yaml.safe_load((ROOT / '.github/workflows/godot-v1.yml').read_text(encoding='utf-8'))['jobs']['godot-v1']['steps']
    godot = os.environ.get('GODOT_BIN', str(default_godot()))
    bash = find_bash()
    with tempfile.TemporaryDirectory() as base:
        shims, scratch = Path(base) / 'bin', Path(base) / 'tmp'
        shims.mkdir()
        scratch.mkdir()
        for name, target in (('godot', godot), ('python', sys.executable)):
            make_shim(shims, name, target)
        env = dict(os.environ, PATH=str(shims) + os.pathsep + os.environ['PATH'])
        for step in steps:
            if 'run' not in step or step['name'].startswith(CI_ONLY):
                continue
            print(f'==> {step["name"]}', flush=True)
            # pipefail so `godot ... | tee` reports Godot's exit code, matching the workflow's own shells.
            if subprocess.run([bash, '-e', '-o', 'pipefail', '-c', step_script(step['run'], scratch)], cwd=ROOT, env=env).returncode:
                sys.exit(f'FAILED step: {step["name"]}')
    print('All Godot qualification steps passed.')


if __name__ == '__main__':
    main()
