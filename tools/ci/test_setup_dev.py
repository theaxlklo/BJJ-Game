"""Tests for tools/setup_dev.py. Everything runs against fake executables in temp directories and an
injected command runner, so no test installs, downloads or modifies anything outside its temp dir."""
import contextlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / 'setup_dev.py'
spec = importlib.util.spec_from_file_location('setup_dev', SCRIPT)
sd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sd)

DIGEST = 'a' * 64
WORKFLOW = f'''curl "https://downloads.godotengine.org/?version=4.7.2&flavor=stable"
echo "{DIGEST}  /tmp/godot.zip" | sha256sum --check
'''
PLUGINS_ENABLED = [{'id': 'ponytail@ponytail', 'version': '5.2.0', 'enabled': True}]


def fake(directory, name, body):
    """A stand-in executable using only shell builtins, so tests can run with an empty PATH."""
    path = Path(directory) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('#!/bin/sh\n' + body + '\n')
    path.chmod(0o755)
    return str(path)


def fake_godot(directory, name, version):
    return fake(directory, name, f'echo "{version}"')


def fake_claude(directory, plugins, marketplaces=(), rc=0):
    body = (f'case "$*" in\n  "--version") echo "9.9.9 (Claude Code)";;\n'
            f"  \"plugin list --json\") echo '{json.dumps(plugins)}'; exit {rc};;\n"
            f"  \"plugin marketplace list --json\") echo '{json.dumps([{'name': m} for m in marketplaces])}';;\n"
            '  *) exit 2;;\nesac')
    return fake(directory, 'claude', body)


class Sandbox(unittest.TestCase):
    """A fake repo root, home directory and empty bin directory per test."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.root, self.home, self.bin = self.tmp / 'repo', self.tmp / 'home', self.tmp / 'bin'
        for d in (self.home, self.bin):
            d.mkdir()
        (self.root / '.github/workflows').mkdir(parents=True)
        (self.root / '.github/workflows/godot-v1.yml').write_text(WORKFLOW)
        for skill in sd.SKILLS:
            (self.root / '.claude/skills' / skill).mkdir(parents=True)
            (self.root / '.claude/skills' / skill / 'SKILL.md').write_text('---\n---\n')
        self.env = {'PATH': str(self.bin), 'HOME': str(self.home)}

    def venv_python(self, importable):
        return fake(self.root / '.venv/bin', 'python', f'exit {0 if importable else 1}')

    def godot_default(self, version='4.7.2.stable.official.abc'):
        return fake_godot(self.home / '.local/bin', 'godot-bjj', version)


class GodotTests(Sandbox):
    def test_default_location_is_ready(self):
        path = self.godot_default()
        c = sd.check_godot(self.root, self.env)
        self.assertEqual((c.status, path in c.detail), (sd.OK, True))

    def test_godot_bin_is_respected(self):
        self.env['GODOT_BIN'] = fake_godot(self.bin, 'custom', '4.7.2.stable.official.x')
        self.assertEqual(sd.check_godot(self.root, self.env).status, sd.OK)

    def test_stale_godot_bin_is_reported_even_when_default_is_fine(self):
        self.godot_default()
        self.env['GODOT_BIN'] = str(self.tmp / 'gone')
        c = sd.check_godot(self.root, self.env)
        self.assertEqual(c.status, sd.MISSING)
        self.assertIn('GODOT_BIN', c.detail)

    def test_wrong_version_is_not_ready(self):
        self.godot_default('4.6.1.stable.official.x')
        c = sd.check_godot(self.root, self.env)
        self.assertEqual(c.status, sd.MISSING)
        self.assertIn('4.6.1', c.detail)

    def test_path_only_install_needs_godot_bin_export(self):
        found = fake_godot(self.bin, 'godot', '4.7.2.stable.official.x')
        c = sd.check_godot(self.root, self.env)
        self.assertEqual(c.status, sd.MISSING)
        self.assertIn(f'export GODOT_BIN={found}', c.hint)

    def test_missing_godot_shows_pin_and_never_offers_a_download(self):
        c = sd.check_godot(self.root, self.env)
        self.assertEqual((c.status, c.fix), (sd.MISSING, ()))
        self.assertTrue(all(s in c.hint for s in ('4.7.2', DIGEST, 'never downloads')))


class PyYamlTests(Sandbox):
    def test_ready_in_project_venv(self):
        self.venv_python(True)
        self.assertEqual(sd.check_pyyaml(self.root, self.env).status, sd.OK)

    def test_missing_in_existing_venv_only_installs_into_it(self):
        python = self.venv_python(False)
        c = sd.check_pyyaml(self.root, self.env)
        self.assertEqual(c.fix, ([python, '-m', 'pip', 'install', 'PyYAML>=6'],))

    def test_missing_without_venv_creates_one_never_touching_system_python(self):
        no_yaml = fake(self.bin, 'py', 'exit 1')
        with mock.patch.object(sd.sys, 'executable', no_yaml):
            c = sd.check_pyyaml(self.root, self.env)
        venv = self.root / '.venv'
        self.assertEqual(c.fix, ([no_yaml, '-m', 'venv', str(venv)], [f'{venv}/bin/python', '-m', 'pip', 'install', 'PyYAML>=6']))
        self.assertIn(f'{venv}/bin/python tools/ci/run_godot_steps.py', c.hint)

    def test_half_made_venv_is_never_overwritten(self):
        (self.root / '.venv').mkdir()
        no_yaml = fake(self.bin, 'py', 'exit 1')
        with mock.patch.object(sd.sys, 'executable', no_yaml):
            c = sd.check_pyyaml(self.root, self.env)
        self.assertEqual((c.status, c.fix), (sd.MISSING, ()))


class PonytailTests(Sandbox):
    def test_enabled(self):
        fake_claude(self.bin, PLUGINS_ENABLED)
        self.assertEqual(sd.check_ponytail(self.env).status, sd.OK)

    def test_disabled_is_reported_not_changed(self):
        fake_claude(self.bin, [{'id': sd.PLUGIN, 'enabled': False}])
        c = sd.check_ponytail(self.env)
        self.assertEqual((c.status, c.fix), (sd.WARN, ()))
        self.assertIn('claude plugin enable', c.hint)

    def test_absent_with_known_marketplace_only_installs_plugin(self):
        claude = fake_claude(self.bin, [], marketplaces=['ponytail'])
        self.assertEqual(sd.check_ponytail(self.env).fix, ([claude, 'plugin', 'install', sd.PLUGIN],))

    def test_absent_adds_marketplace_first(self):
        claude = fake_claude(self.bin, [])
        self.assertEqual(sd.check_ponytail(self.env).fix,
                         ([claude, 'plugin', 'marketplace', 'add', 'DietrichGebert/ponytail'], [claude, 'plugin', 'install', sd.PLUGIN]))

    def test_unreadable_output_and_cli_failure_offer_nothing(self):
        fake(self.bin, 'claude', 'echo "not json"')
        self.assertEqual(sd.check_ponytail(self.env).fix, ())
        fake_claude(self.bin, [], rc=1)
        c = sd.check_ponytail(self.env)
        self.assertEqual((c.status, c.fix), (sd.WARN, ()))

    def test_no_claude_code(self):
        self.assertEqual(sd.check_claude(self.env).status, sd.WARN)
        self.assertEqual(sd.check_ponytail(self.env).fix, ())


class SkillAndCodexTests(Sandbox):
    def test_skills_present_and_missing(self):
        self.assertEqual(sd.check_skills(self.root).status, sd.OK)
        (self.root / '.claude/skills/systematic-debugging/SKILL.md').unlink()
        c = sd.check_skills(self.root)
        self.assertEqual(c.status, sd.MISSING)
        self.assertIn('systematic-debugging', c.detail)

    def test_codex_is_optional_and_never_fixable(self):
        c = sd.check_codex(self.env)
        self.assertEqual((c.status, c.fix), (sd.INFO, ()))
        fake(self.bin, 'codex', 'echo "codex-cli 0.1"')
        self.assertEqual(sd.check_codex(self.env).status, sd.OK)


class MainTests(Sandbox):
    """End-to-end through main() with an injected runner: nothing real is installed."""

    def ready(self):
        self.venv_python(True)
        self.godot_default()
        fake_claude(self.bin, PLUGINS_ENABLED)

    def run_main(self, argv, answers=(), interactive=True, runner=None):
        calls, asked = [], []
        answers = iter(answers)

        def default_runner(argv_, env):
            calls.append(argv_)
            return 0, ''

        def ask(prompt):
            asked.append(prompt)
            return next(answers, 'n')

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = sd.main(argv, env=self.env, root=self.root, ask=ask,
                           runner=runner or default_runner, interactive=interactive)
        return code, out.getvalue(), calls, asked

    def test_ready_machine_exits_zero_and_names_the_runner_command(self):
        self.ready()
        code, out, _, _ = self.run_main([])
        self.assertEqual(code, 0)
        self.assertIn('tools/ci/run_godot_steps.py', out)
        self.assertIn(str(self.root / '.venv/bin/python'), out)

    def test_missing_required_tool_exits_one(self):
        self.ready()
        (self.home / '.local/bin/godot-bjj').unlink()
        code, out, _, _ = self.run_main([])
        self.assertEqual(code, 1)
        self.assertIn('Not ready: Godot', out)

    def test_default_run_never_modifies_anything(self):
        self.venv_python(False)
        before = sorted(p for p in self.tmp.rglob('*'))
        _, out, calls, asked = self.run_main([])
        self.assertEqual((calls, asked, before), ([], [], sorted(p for p in self.tmp.rglob('*'))))
        self.assertIn('--install', out)

    def test_noninteractive_install_changes_nothing(self):
        self.venv_python(False)
        code, out, calls, asked = self.run_main(['--install'], interactive=False)
        self.assertEqual((calls, asked, code), ([], [], 1))
        self.assertIn('Nothing was changed', out)

    def test_declining_runs_nothing(self):
        self.venv_python(False)
        _, out, calls, _ = self.run_main(['--install'], answers=['n'])
        self.assertEqual(calls, [])
        self.assertIn('Skipped', out)

    def test_confirmed_install_runs_exactly_the_shown_commands(self):
        python = self.venv_python(False)
        fake_claude(self.bin, [], marketplaces=['ponytail'])
        _, out, calls, asked = self.run_main(['--install'], answers=['y', 'y'])
        claude = str(self.bin / 'claude')
        self.assertEqual(calls, [[python, '-m', 'pip', 'install', 'PyYAML>=6'], [claude, 'plugin', 'install', sd.PLUGIN]])
        self.assertEqual(len(asked), 2)
        self.assertIn('Commands that would run', out)

    def test_failing_command_stops_that_component_and_reports(self):
        self.venv_python(False)
        seen = []

        def failing(argv, env):
            seen.append(argv)
            return (1, 'boom') if argv[1:3] == ['-m', 'pip'] else (0, '')

        _, out, _, _ = self.run_main(['--install'], answers=['y'], runner=failing)
        self.assertEqual(len(seen) >= 1, True)
        self.assertIn('FAILED (1)', out)
        self.assertIn('boom', out)

    def test_rerun_on_ready_machine_offers_nothing(self):
        self.ready()
        _, _, calls, asked = self.run_main(['--install'])
        self.assertEqual((calls, asked), ([], []))

    def test_optional_codex_missing_does_not_block(self):
        self.ready()
        self.assertEqual(self.run_main([])[0], 0)


class ProcessTests(unittest.TestCase):
    def test_real_script_without_tools_fails_cleanly_and_noninteractively(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = {'PATH': tmp, 'HOME': tmp}
            repo_venv = SCRIPT.parents[1] / '.venv'
            existed = repo_venv.exists()
            for args in ([], ['--install']):
                done = subprocess.run([sys.executable, str(SCRIPT), *args], env=env, stdin=subprocess.DEVNULL,
                                      capture_output=True, text=True, timeout=60)
                self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
                self.assertIn('Godot', done.stdout)
                self.assertIn('4.7.2', done.stdout)
                self.assertNotIn('Traceback', done.stderr)
            self.assertEqual(repo_venv.exists(), existed)


if __name__ == '__main__':
    unittest.main(verbosity=2)
