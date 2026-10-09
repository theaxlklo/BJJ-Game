"""Routing false-negative regressions, independent of gameplay test discovery."""
import subprocess
import tempfile
import unittest
from pathlib import Path
from route import classify, changed_paths, plan


class RoutingTests(unittest.TestCase):
    def test_path_matrix(self):
        cases = [
            ('gdscript', ['GODOT_V1/scripts/a.gd'], 'GODOT_ONLY', False, True),
            ('scene', ['GODOT_V1/scenes/a.tscn'], 'GODOT_ONLY', False, True),
            ('fixture generator', ['GODOT_V1/tests/generate.py'], 'GODOT_ONLY', False, True),
            ('python source', ['src/a.py'], 'PYTHON_OR_SHARED', True, True),
            ('python tests', ['tests/test_a.py'], 'PYTHON_OR_SHARED', True, True),
            ('mixed', ['src/a.py', 'GODOT_V1/a.gd'], 'PYTHON_OR_SHARED', True, True),
            ('workflow', ['.github/workflows/godot-v1.yml'], 'CI_INFRASTRUCTURE', True, True),
            ('classifier', ['tools/ci/route.py'], 'CI_INFRASTRUCTURE', True, True),
            ('documentation', ['docs/ci/usage.md'], 'DOCUMENTATION_ONLY', False, False),
            ('evidence', ['docs/evidence/a.md'], 'PYTHON_OR_SHARED', True, True),
            ('contract', ['docs/BJJ_GAME_MASTER_DEVELOPMENT_GUIDE.md'], 'PYTHON_OR_SHARED', True, True),
            ('pinned measurement', ['docs/HANDOFF_OSCILLATION_D2_V1E_MEASUREMENT_DATA.md'], 'PYTHON_OR_SHARED', True, True),
            ('frozen preregistration', ['docs/BURST_RECOVERY_LOCKOUT_D3B_PREREGISTRATION.md'], 'PYTHON_OR_SHARED', True, True),
            ('unknown', ['mystery'], 'UNKNOWN', True, True),
            ('mixed documentation and CI', ['README.md', 'tools/ci/test_route.py'], 'CI_INFRASTRUCTURE', True, True),
            ('empty', [], 'UNKNOWN', True, True),
            ('traversal', ['GODOT_V1/../src/a.py'], 'UNKNOWN', True, True),
            ('absolute', ['/GODOT_V1/a.gd'], 'UNKNOWN', True, True),
        ]
        for name, paths, category, python, godot in cases:
            with self.subTest(name=name):
                result = classify(paths)
                self.assertEqual((result['category'], result['python_required'], result['godot_required']), (category, python, godot))

    def test_events(self):
        for event in ('pull_request', 'push'):
            with self.subTest(event=event):
                self.assertFalse(plan(['GODOT_V1/a.gd'], event, 'refs/heads/feature')['python_required'])
        self.assertTrue(plan(['README.md'], 'push', 'refs/heads/main')['python_required'])
        self.assertTrue(plan(['GODOT_V1/a.gd'], 'workflow_dispatch', 'refs/heads/feature', full=True)['python_required'])
        self.assertTrue(plan(['README.md'], 'missing', '')['python_required'])

    def test_git_ranges_and_renames(self):
        with tempfile.TemporaryDirectory() as directory:
            def git(*args):
                return subprocess.check_output(['git', '-C', directory, *args]).decode().strip()
            git('init', '-q'); git('config', 'user.name', 'CI test'); git('config', 'user.email', 'ci@example.invalid')
            root = Path(directory)
            (root / 'GODOT_V1').mkdir(); (root / 'GODOT_V1/a.gd').write_text('initial\n')
            git('add', '.'); git('commit', '-qm', 'base'); base = git('rev-parse', 'HEAD')
            (root / 'GODOT_V1/a.gd').write_text('initial\nadded\n'); git('commit', '-qam', 'first')
            (root / 'GODOT_V1/new.gd').write_text('new\n'); git('add', '.'); git('commit', '-qm', 'second'); head = git('rev-parse', 'HEAD')
            self.assertEqual(set(changed_paths(base, head, False, directory)), {'GODOT_V1/a.gd', 'GODOT_V1/new.gd'})
            # A stacked PR compares to its own base, not main or the latest commit.
            self.assertEqual(set(changed_paths(base, head, True, directory)), {'GODOT_V1/a.gd', 'GODOT_V1/new.gd'})
            (root / 'src').mkdir(); git('mv', 'GODOT_V1/new.gd', 'src/new.py'); git('commit', '-qm', 'move')
            moved = changed_paths(head, git('rev-parse', 'HEAD'), True, directory)
            self.assertEqual(set(moved), {'GODOT_V1/new.gd', 'src/new.py'})
            self.assertTrue(classify(moved)['python_required'])
            head = git('rev-parse', 'HEAD'); git('rm', 'src/new.py'); git('commit', '-qm', 'delete')
            self.assertEqual(changed_paths(head, git('rev-parse', 'HEAD'), False, directory), ['src/new.py'])
            with self.assertRaises((ValueError, subprocess.CalledProcessError)):
                changed_paths('0' * 40, head, True, directory)


class EventAdmissionTests(unittest.TestCase):
    def test_missing_pr_fields_and_stale_manual_sha(self):
        import json
        import os
        with tempfile.TemporaryDirectory() as directory:
            def git(*args):
                return subprocess.check_output(['git', '-C', directory, *args]).decode().strip()
            git('init', '-q'); git('config', 'user.name', 'CI'); git('config', 'user.email', 'ci@example.invalid')
            root = Path(directory); (root / 'README.md').write_text('test\n')
            git('add', '.'); git('commit', '-qm', 'initial'); head = git('rev-parse', 'HEAD')
            script = str(Path(__file__).with_name('route.py').resolve())
            cases = [
                ('pull_request', {'pull_request': {'head': {'sha': head}}}, True),
                ('pull_request', {}, False),
                ('push', {'before': '0' * 40}, True),
                ('workflow_dispatch', {'inputs': {'target_sha': 'a' * 40, 'full_qualification': 'true'}}, False),
                ('workflow_dispatch', {'inputs': {'target_sha': head, 'full_qualification': 'true'}}, True),
            ]
            for name, event, accepted in cases:
                with self.subTest(event=name, payload=event):
                    payload = root / 'event.json'; payload.write_text(json.dumps(event))
                    output = root / 'outputs'; output.write_text('')
                    env = dict(os.environ, GITHUB_EVENT_PATH=str(payload), GITHUB_OUTPUT=str(output), GITHUB_EVENT_NAME=name, GITHUB_SHA=head, GITHUB_REF='refs/heads/feature')
                    run = subprocess.run(['python', script], cwd=directory, env=env, capture_output=True, text=True)
                    self.assertEqual(run.returncode == 0, accepted, run.stderr)
                    if accepted:
                        self.assertIn('python_required=true', output.read_text())
                        self.assertIn('godot_required=true', output.read_text())
                    else:
                        self.assertEqual(output.read_text(), '')


class GateTests(unittest.TestCase):
    def test_real_gate_failure_propagation(self):
        import os
        workflow = Path(__file__).resolve().parents[2] / '.github/workflows/test.yml'
        text = workflow.read_text().split('  ci-gate:', 1)[1]
        script = text.split('        run: |\n', 1)[1]
        script = '\n'.join(line[10:] for line in script.splitlines())
        baseline = dict(CLASSIFY_RESULT='success', LIGHT_RESULT='success', PYTHON_REQUIRED='false', GODOT_REQUIRED='true', GODOT_RESULT='success', UNIT_RESULT='skipped', VERIFY_RESULT='skipped', HISTORY_RESULT='skipped')
        cases = [('godot only', {}, True), ('docs only', {'GODOT_REQUIRED': 'false', 'GODOT_RESULT': 'skipped'}, True), ('full', {'PYTHON_REQUIRED': 'true', 'UNIT_RESULT': 'success', 'VERIFY_RESULT': 'success', 'HISTORY_RESULT': 'success'}, True)]
        for key in ('CLASSIFY_RESULT', 'LIGHT_RESULT', 'GODOT_RESULT'):
            for state in ('failure', 'cancelled', 'skipped'):
                cases.append((key + state, {key: state}, False))
        for key in ('PYTHON_REQUIRED', 'GODOT_REQUIRED'):
            cases.append((key + 'missing', {key: ''}, False))
        for key in ('UNIT_RESULT', 'VERIFY_RESULT', 'HISTORY_RESULT'):
            cases.append((key + 'unexpected success', {key: 'success'}, False))
            full = dict(PYTHON_REQUIRED='true', UNIT_RESULT='success', VERIFY_RESULT='success', HISTORY_RESULT='success')
            full[key] = 'failure'; cases.append((key + 'full failure', full, False))
        for name, changes, accepted in cases:
            with self.subTest(name=name):
                result = subprocess.run(['bash', '-c', script], env=dict(os.environ, **(baseline | changes)), capture_output=True, text=True)
                self.assertEqual(result.returncode == 0, accepted, result.stderr)


class LightweightTests(unittest.TestCase):
    def test_shallow_root_does_not_recheck_historical_whitespace(self):
        import os
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository = root / 'repository'; repository.mkdir()
            def git(*args):
                return subprocess.check_output(['git', '-C', str(repository), *args]).decode().strip()
            git('init', '-q'); git('config', 'user.name', 'CI'); git('config', 'user.email', 'ci@example.invalid')
            (repository / 'old.md').write_text('Historical Markdown break  \n')
            git('add', '.'); git('commit', '-qm', 'historical'); base = git('rev-parse', 'HEAD')
            (repository / 'new.md').write_text('Clean changed documentation\n')
            git('add', '.'); git('commit', '-qm', 'new'); head = git('rev-parse', 'HEAD')
            shallow = root / 'shallow'
            subprocess.check_call(['git', 'clone', '-q', '--depth=1', repository.as_uri(), str(shallow)])
            old = subprocess.run(['git', 'show', '--format=', '--check', 'HEAD'], cwd=shallow, capture_output=True)
            self.assertNotEqual(old.returncode, 0, 'reproduce the depth-one historical-whitespace failure')
            workflow = Path(__file__).resolve().parents[2] / '.github/workflows/test.yml'
            section = workflow.read_text().split('  lightweight-validation:', 1)[1].split('  godot:', 1)[0]
            self.assertIn('fetch-depth: 0', section)
            script = section.split('        run: |\n', 1)[1]
            script = '\n'.join(line[10:] for line in script.splitlines())
            result = subprocess.run(['bash', '-c', script], cwd=repository, env=dict(os.environ, DIFF_SPAN=base+'...'+head), capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
