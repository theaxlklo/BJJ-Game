"""Tests for the platform helpers behind tools/ci/run_godot_steps.py, for Linux and Windows alike.

Pure helpers take `windows=` so both platforms' behavior is checked on any machine; the two tests that need a
real Windows (a sh wrapper actually executing, Git Bash actually found) skip elsewhere."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from godot_runner_support import default_godot, find_bash, make_shim, step_script


class StepScriptTests(unittest.TestCase):
    SCRIPT = "godot ... | tee /tmp/a.log\npython - <<'PY'\nPath('/tmp/a.log')\nPY"

    def test_linux_text_is_untouched(self):
        self.assertEqual(step_script(self.SCRIPT, Path('/scratch'), windows=False), self.SCRIPT)

    def test_windows_rewrites_every_tmp_log_path_to_forward_slashes(self):
        out = step_script(self.SCRIPT, Path('C:/Users/x/Temp/run/tmp'), windows=True)
        self.assertNotIn('/tmp/a.log', out.replace('Temp/run/tmp/a.log', ''))
        self.assertEqual(out.count('C:/Users/x/Temp/run/tmp/a.log'), 2)

    def test_the_real_workflow_only_uses_tmp_as_a_path_prefix(self):
        """The rewrite assumes `/tmp/` followed by a name; flag any other spelling a future step might add."""
        import re
        text = (Path(__file__).resolve().parents[2] / '.github/workflows/godot-v1.yml').read_text(encoding='utf-8')
        self.assertEqual(re.findall(r'/tmp(?!/)', text), [])


class DefaultGodotTests(unittest.TestCase):
    def test_default_name_per_platform(self):
        self.assertEqual(default_godot(windows=False).name, 'godot-bjj')
        self.assertEqual(default_godot(windows=True).name, 'godot-bjj.exe')
        self.assertEqual(default_godot(windows=True).parent, Path.home() / '.local' / 'bin')


class ShimTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)

    @unittest.skipIf(os.name == 'nt', 'creating symlinks needs special privileges on Windows')
    def test_linux_shim_is_a_symlink_to_the_target(self):
        shim = make_shim(self.dir, 'godot', '/opt/godot', windows=False)
        self.assertTrue(shim.is_symlink())
        self.assertEqual(os.readlink(shim), '/opt/godot')

    def test_windows_shim_is_a_sh_wrapper_with_a_quoted_forward_slash_path(self):
        shim = make_shim(self.dir, 'godot', r'C:\Tools\God ot\godot.exe', windows=True)
        self.assertFalse(shim.is_symlink())
        self.assertEqual(shim.read_bytes(), b"#!/bin/sh\nexec 'C:/Tools/God ot/godot.exe' \"$@\"\n")

    @unittest.skipUnless(os.name == 'nt', 'needs Git Bash on Windows')
    def test_windows_shim_really_runs_the_target_and_forwards_arguments_and_exit_code(self):
        shim = make_shim(self.dir, 'python', sys.executable, windows=True)
        bash = find_bash()
        done = subprocess.run([bash, '-c', f'PATH="{self.dir.as_posix()}:$PATH"; python -c "import sys; print(sys.argv[1:]); sys.exit(7)" a "b c"'],
                              capture_output=True, text=True)
        self.assertEqual((done.returncode, done.stdout.strip()), (7, "['a', 'b c']"))


class FindBashTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def git_install(self, layout='bin'):
        (self.root / 'Git' / 'cmd').mkdir(parents=True)
        (self.root / 'Git' / 'cmd' / 'git.exe').write_bytes(b'')
        (self.root / 'Git' / layout).mkdir(parents=True, exist_ok=True)
        (self.root / 'Git' / layout / 'bash.exe').write_bytes(b'')
        return str(self.root / 'Git' / 'cmd' / 'git.exe')

    def test_linux_just_uses_bash(self):
        self.assertEqual(find_bash(windows=False, which=lambda name, path=None: '/usr/bin/bash'), '/usr/bin/bash')

    def test_windows_prefers_git_bash_next_to_git_never_the_wsl_launcher(self):
        git = self.git_install()
        # A bare `bash` lookup would return the WSL launcher; it must never be consulted or returned.
        which = lambda name, path=None: git if name == 'git' else r'C:\Windows\System32\bash.exe'
        self.assertEqual(find_bash(windows=True, env={}, which=which), str(self.root / 'Git' / 'bin' / 'bash.exe'))

    def test_windows_falls_back_to_the_usr_bin_layout(self):
        git = self.git_install('usr/bin')
        self.assertEqual(find_bash(windows=True, env={}, which=lambda n, path=None: git),
                         str(self.root / 'Git' / 'usr' / 'bin' / 'bash.exe'))

    def test_windows_falls_back_to_program_files_when_git_is_not_on_path(self):
        self.git_install()
        self.assertEqual(find_bash(windows=True, env={'ProgramFiles': str(self.root)}, which=lambda n, path=None: None),
                         str(self.root / 'Git' / 'bin' / 'bash.exe'))

    def test_windows_without_git_bash_explains_the_fix(self):
        with self.assertRaises(FileNotFoundError) as caught:
            find_bash(windows=True, env={}, which=lambda n, path=None: None)
        self.assertIn('Git for Windows', str(caught.exception))

    @unittest.skipUnless(os.name == 'nt' and shutil.which('git'), 'needs Git for Windows')
    def test_the_real_windows_machine_resolves_git_bash(self):
        self.assertTrue(find_bash().lower().endswith(os.path.join('git', 'bin', 'bash.exe')))


if __name__ == '__main__':
    unittest.main(verbosity=2)
