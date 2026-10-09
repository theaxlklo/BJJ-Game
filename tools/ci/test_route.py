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


if __name__ == '__main__':
    unittest.main(verbosity=2)
