#!/usr/bin/env python3
"""BJJ-Game development setup checker: `python3 tools/setup_dev.py` (read-only by default).

Reports what is ready or missing for local-first development (see AGENTS.md). Runs on Linux and native
Windows (PowerShell or Git Bash); platform differences live in the small helpers below. With --install it offers,
one component at a time and only after you confirm, the installs that are safe to automate: PyYAML in a
project-local .venv, and the Ponytail Claude Code plugin. It never uses sudo, never touches system Python
packages, never overwrites an existing configuration and never downloads Godot. Standard library only,
so it runs before anything else is installed. Safe to rerun: nothing is offered once a check passes.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IS_WINDOWS = os.name == 'nt'      # tests patch this to exercise both platforms' path logic anywhere
MIN_PYTHON = (3, 11)             # the supported CI lanes are 3.11 and 3.13
GODOT_PINNED = '4.7.2'
# Official SHA-512 of Godot_v4.7.2-stable_win64.exe.zip, from the godot-builds release's SHA512-SUMS.txt.
GODOT_WINDOWS_SHA512 = ('83decd58fdf67b9d657958a1ae6bf1929c20785315a81effe245874cdc57acb7'
                        '09bf868e00778a96984338c1b29dafdb453c6847747694621c6ecf5da2259993')
GODOT_WINDOWS_URL = 'https://downloads.godotengine.org/?version=4.7.2&flavor=stable&platform=windows.64&slug=win64.exe.zip'
GODOT_WINDOWS_SUMS = 'https://github.com/godotengine/godot-builds/releases/download/4.7.2-stable/SHA512-SUMS.txt'
SKILLS = ('godot-gdscript', 'godot-ui-control', 'systematic-debugging')
PLUGIN = 'ponytail@ponytail'
MARKETPLACE = ('ponytail', 'DietrichGebert/ponytail')   # (marketplace name, GitHub source)

# OK = ready; MISSING = required and not ready (exit code 1); WARN = recommended, not blocking;
# INFO = optional.
OK, MISSING, WARN, INFO = 'OK', 'MISSING', 'WARN', 'INFO'


@dataclass
class Check:
    name: str
    status: str
    detail: str
    hint: str = ''
    fix: tuple = ()      # argv lists offered by --install; empty means nothing safe to automate


def run(argv, env=None, timeout=60):
    """Run argv (never a shell string) and return (returncode, combined output); failures become rc 127."""
    try:
        done = subprocess.run(argv, env=env, capture_output=True, text=True, encoding='utf-8', errors='replace',
                              timeout=timeout)
        return done.returncode, (done.stdout + done.stderr).strip()
    except (OSError, subprocess.TimeoutExpired) as error:
        return 127, str(error)


def venv_python_path(root):
    """Where a project-local .venv keeps its interpreter: Scripts/python.exe on Windows, bin/python elsewhere."""
    return root / '.venv' / ('Scripts' if IS_WINDOWS else 'bin') / ('python.exe' if IS_WINDOWS else 'python')


def default_godot(home):
    """The location run_godot_steps.py falls back to when GODOT_BIN is unset. Windows has no conventional
    per-user bin directory, so the same ~/.local/bin spot is used with an .exe name; most Windows setups
    simply set GODOT_BIN to the *_console.exe (the plain .exe is a GUI program and prints nothing)."""
    return home / '.local' / 'bin' / ('godot-bjj.exe' if IS_WINDOWS else 'godot-bjj')


def project_python(root):
    """The interpreter whose PyYAML matters: run_godot_steps.py hands its own interpreter to the workflow
    steps, so the project .venv is preferred when it exists and the current interpreter otherwise."""
    venv_python = venv_python_path(root)
    return str(venv_python) if venv_python.exists() else sys.executable


def check_python():
    version = '.'.join(map(str, sys.version_info[:3]))
    where = f'{version} ({sys.executable})'
    if sys.version_info[:2] >= MIN_PYTHON:
        return Check('Python', OK, where)
    return Check('Python', MISSING, where, f'Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ is required.')


def check_pyyaml(root, env):
    interpreter = project_python(root)
    if run([interpreter, '-c', 'import yaml'], env)[0] == 0:
        return Check('PyYAML', OK, f'importable by {interpreter}',
                     'Run the Godot runner with exactly this interpreter.' if '.venv' in interpreter else '')
    venv = root / '.venv'
    venv_python = venv_python_path(root)
    hint = f'Run the runner with the interpreter that has PyYAML, e.g. {venv_python} tools/ci/run_godot_steps.py'
    if venv.exists() and not venv_python.exists():
        # A half-made .venv is user state; refuse to overwrite it.
        return Check('PyYAML', MISSING, f'{venv} exists but has no interpreter',
                     f'Remove or repair {venv} yourself, then rerun. {hint}')
    install = [str(venv_python), '-m', 'pip', 'install', 'PyYAML>=6']
    create = [] if venv.exists() else [[sys.executable, '-m', 'venv', str(venv)]]
    return Check('PyYAML', MISSING, f'not importable by {interpreter}', hint, tuple(create + [install]))


def godot_download_hint(root):
    """Show the pinned download so the user can fetch and verify it; on Linux the checksum comes from the
    workflow that CI uses, so there is a single source of truth."""
    if IS_WINDOWS:
        return (f'Needs Godot {GODOT_PINNED}-stable Standard (not .NET), Windows x86_64. This script never downloads it.\n'
                f'  Download: {GODOT_WINDOWS_URL}\n'
                f'  Verify:   sha512 {GODOT_WINDOWS_SHA512}\n'
                f'            (official list: {GODOT_WINDOWS_SUMS})\n'
                f'  Install:  unzip, then set GODOT_BIN to the *_console.exe, e.g.\n'
                f'            setx GODOT_BIN "C:\\Tools\\Godot\\Godot_v{GODOT_PINNED}-stable_win64_console.exe"')
    text = (root / '.github/workflows/godot-v1.yml').read_text() if (root / '.github/workflows/godot-v1.yml').exists() else ''
    url = re.search(r'"(https://downloads\.godotengine\.org/[^"]+)"', text)
    digest = re.search(r'"([0-9a-f]{64})  /tmp/godot\.zip"', text)
    return (f'Needs Godot {GODOT_PINNED}-stable Standard (not .NET), Linux x86_64. This script never downloads it.\n'
            f'  Download: {url.group(1) if url else "see .github/workflows/godot-v1.yml"}\n'
            f'  Verify:   sha256 {digest.group(1) if digest else "(see the workflow)"}\n'
            f'  Install:  unzip, then symlink the binary to ~/.local/bin/godot-bjj (or export GODOT_BIN=/path/to/godot)')


def godot_version(path, env):
    rc, out = run([path, '--headless', '--version'], env, timeout=20)
    return out.splitlines()[0] if rc == 0 and out else ''


def check_godot(root, env):
    home = Path(env.get('HOME') or env.get('USERPROFILE') or Path.home())
    default = default_godot(home)
    explicit = env.get('GODOT_BIN')
    # run_godot_steps.py reads only GODOT_BIN, then the default location, never PATH. A set GODOT_BIN wins
    # even when the default is fine, so a stale value must be reported rather than silently bypassed.
    for label, path in (('GODOT_BIN', explicit), ('default location', str(default))):
        if not path or not (os.path.isfile(path) and os.access(path, os.X_OK)):
            if label == 'GODOT_BIN' and path:
                return Check('Godot', MISSING, f'GODOT_BIN={path} is not an executable file',
                             'Fix or unset GODOT_BIN.\n  ' + godot_download_hint(root))
            continue
        version = godot_version(path, env)
        if version.startswith(GODOT_PINNED + '.stable'):
            return Check('Godot', OK, f'{path} ({version})')
        return Check('Godot', MISSING, f'{path} reports {version or "no version"}, need {GODOT_PINNED}.stable',
                     godot_download_hint(root))
    for name in ('godot-bjj', 'godot', 'godot4', f'Godot_v{GODOT_PINNED}-stable_win64_console'):
        found = shutil.which(name, path=env.get('PATH', ''))
        if found and godot_version(found, env).startswith(GODOT_PINNED + '.stable'):
            advice = (f'Run: setx GODOT_BIN "{found}"   (new terminals pick it up)' if IS_WINDOWS
                      else f'Run: export GODOT_BIN={found}   (or symlink it to {default})')
            return Check('Godot', MISSING, f'{GODOT_PINNED} found on PATH at {found}, but the runner ignores PATH', advice)
    return Check('Godot', MISSING, 'no Godot executable found', godot_download_hint(root))


def check_claude(env):
    found = shutil.which('claude', path=env.get('PATH', ''))
    if not found:
        return Check('Claude Code', WARN, 'not installed', 'Optional but recommended: https://claude.com/claude-code')
    return Check('Claude Code', OK, f'{found} ({run([found, "--version"], env)[1] or "version unknown"})')


def check_ponytail(env):
    claude = shutil.which('claude', path=env.get('PATH', ''))
    if not claude:
        return Check('Ponytail', WARN, 'needs Claude Code first')
    # --json: structured output survives CLI wording changes, unlike scraping the pretty list.
    rc, out = run([claude, 'plugin', 'list', '--json'], env)
    try:
        plugins = json.loads(out) if rc == 0 else None
    except ValueError:
        plugins = None
    if not isinstance(plugins, list):
        return Check('Ponytail', WARN, 'could not read `claude plugin list --json`', 'Check manually: claude plugin list')
    plugin = next((p for p in plugins if isinstance(p, dict) and p.get('id') == PLUGIN), None)
    if plugin and plugin.get('enabled'):
        return Check('Ponytail', OK, f'{PLUGIN} {plugin.get("version", "?")} enabled')
    if plugin:
        return Check('Ponytail', WARN, f'{PLUGIN} installed but disabled', f'Enable it yourself: claude plugin enable {PLUGIN}')
    rc, out = run([claude, 'plugin', 'marketplace', 'list', '--json'], env)
    try:
        known = {m.get('name') for m in json.loads(out)} if rc == 0 else set()
    except (ValueError, AttributeError):
        known = set()
    add = [] if MARKETPLACE[0] in known else [[claude, 'plugin', 'marketplace', 'add', MARKETPLACE[1]]]
    return Check('Ponytail', WARN, f'{PLUGIN} not installed',
                 f'Downloads the plugin from github.com/{MARKETPLACE[1]} and registers its hooks in Claude Code.',
                 tuple(add + [[claude, 'plugin', 'install', PLUGIN]]))


def check_skills(root):
    missing = [s for s in SKILLS if not (root / '.claude' / 'skills' / s / 'SKILL.md').is_file()]
    if not missing:
        return Check('Repo skills', OK, ', '.join(SKILLS))
    return Check('Repo skills', MISSING, 'missing: ' + ', '.join(missing), 'They ship with the repo: git pull, or git checkout -- .claude/skills')


def check_codex(env):
    found = shutil.which('codex', path=env.get('PATH', ''))
    if not found:
        return Check('Codex CLI', INFO, 'not installed (optional; this script does not install it)')
    return Check('Codex CLI', OK, f'{found} ({run([found, "--version"], env)[1] or "version unknown"})')


def all_checks(root, env):
    return [check_python(), check_pyyaml(root, env), check_godot(root, env), check_claude(env),
            check_ponytail(env), check_skills(root), check_codex(env)]


def report(checks, root, out=print):
    for c in checks:
        out(f'[{c.status:^7}] {c.name:<12} {c.detail}')
        for line in filter(None, c.hint.splitlines()):
            out(f'            {line}')
    blocked = [c.name for c in checks if c.status == MISSING]
    python = project_python(root)
    out('\n' + (f'Not ready: {", ".join(blocked)}.' if blocked else 'Ready. Local Godot qualification:'))
    if not blocked:
        out(f'  {python} tools/ci/run_godot_steps.py')
    return 1 if blocked else 0


def offer_fixes(checks, ask, runner, env, out=print):
    """Offer each safe install separately. Declining or a failing command stops that component only."""
    for c in checks:
        if c.status == OK or not c.fix:
            continue
        out(f'\n{c.name}: {c.detail}\n  {c.hint}\n  Commands that would run:')
        for argv in c.fix:
            out('    ' + ' '.join(argv))
        if ask('  Run these now? [y/N] ').strip().lower() not in ('y', 'yes'):
            out('  Skipped.')
            continue
        for argv in c.fix:
            rc, text = runner(argv, env)
            if rc != 0:
                out(f'  FAILED ({rc}): {" ".join(argv)}\n  {text[-400:]}\n  Run the commands above yourself once the cause is fixed.')
                break
        else:
            out('  Done.')


def main(argv=None, *, env=None, root=ROOT, ask=input, runner=run, interactive=None):
    parser = argparse.ArgumentParser(description='Check (and optionally set up) a BJJ-Game development machine.')
    parser.add_argument('--install', action='store_true', help='interactively offer safe installs for missing components')
    args = parser.parse_args(argv)
    env = dict(os.environ if env is None else env)
    interactive = sys.stdin.isatty() if interactive is None else interactive
    checks = all_checks(root, env)
    code = report(checks, root)
    if not args.install:
        if any(c.fix for c in checks):
            print('\nSome items can be installed safely: rerun with --install (interactive).')
        return code
    if not interactive:
        # Confirmation is the safety guarantee, so without a terminal nothing may be installed.
        print('\n--install needs an interactive terminal to ask for confirmation. Nothing was changed.')
        return code
    offer_fixes(checks, ask, runner, env)
    print('\nRechecking:\n')
    return report(all_checks(root, env), root)


if __name__ == '__main__':
    sys.exit(main())
