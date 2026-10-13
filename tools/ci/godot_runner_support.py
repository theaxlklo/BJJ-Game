r"""Platform helpers for run_godot_steps.py (standard library only, so tests run without PyYAML).

Finding a real POSIX bash:

On Linux and macOS this is simply `bash`. On Windows a bare `bash` often resolves to C:\Windows\System32\bash.exe,
the WSL launcher, which fails when no Linux distribution is installed and would run the steps in the wrong
environment even when one is. The workflow steps are written for Git for Windows' bash, so that is the only
Windows bash accepted here.
"""
import os
import shlex
import shutil
from pathlib import Path, PureWindowsPath


def find_bash(windows=None, env=None, which=shutil.which):
    """Return the bash executable to run workflow steps with, or raise FileNotFoundError with a fix."""
    windows = os.name == 'nt' if windows is None else windows
    env = os.environ if env is None else env
    if not windows:
        return which('bash') or 'bash'
    candidates = []
    git = which('git', path=env.get('PATH'))
    if git:
        # ...\Git\cmd\git.exe (the PATH entry) or ...\Git\bin\git.exe both sit one level below the install root.
        root = Path(git).resolve().parents[1]
        candidates += [root / 'bin' / 'bash.exe', root / 'usr' / 'bin' / 'bash.exe']
    for variable in ('ProgramFiles', 'ProgramW6432', 'LOCALAPPDATA'):
        base = env.get(variable)
        if base:
            suffix = Path('Programs') / 'Git' if variable == 'LOCALAPPDATA' else Path('Git')
            candidates.append(Path(base) / suffix / 'bin' / 'bash.exe')
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    raise FileNotFoundError('Git Bash was not found. Install Git for Windows (winget install -e --id Git.Git) '
                            'and make sure git is on PATH; the WSL bash.exe is deliberately not used.')


def default_godot(windows=None):
    windows = os.name == 'nt' if windows is None else windows
    return Path.home() / '.local' / 'bin' / ('godot-bjj.exe' if windows else 'godot-bjj')


def make_shim(directory, name, target, windows=None):
    """Make `name` on a PATH directory run `target`. A symlink where that works, a sh wrapper on Windows.

    Forward slashes are used inside the wrapper because Git Bash accepts them for Windows paths while a
    backslash would be an escape character to the shell. PureWindowsPath (not Path) parses the target as a Windows path on every
    OS, so the conversion is the same on a Linux test run as on real Windows."""
    windows = os.name == 'nt' if windows is None else windows
    shim = Path(directory) / name
    if not windows:
        shim.symlink_to(target)
        return shim
    shim.write_text(f'#!/bin/sh\nexec {shlex.quote(PureWindowsPath(target).as_posix())} "$@"\n', encoding='utf-8', newline='\n')
    return shim


def step_script(script, scratch, windows=None):
    """The step's shell text, with the workflow's /tmp/ log paths pointed at `scratch` on Windows only."""
    windows = os.name == 'nt' if windows is None else windows
    return script.replace('/tmp/', Path(scratch).as_posix() + '/') if windows else script
