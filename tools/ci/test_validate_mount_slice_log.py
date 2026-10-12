"""Synthetic and real-log regressions for the Mount-slice false-success guard."""
import contextlib
import io
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from validate_mount_slice_log import main, validate

EXPECTED = 256992
WORKFLOW = Path(__file__).resolve().parents[2] / '.github' / 'workflows' / 'godot-v1.yml'

# Verbatim output of a clean run of the qualified A3d test (local and GitHub CI).
REAL_CLEAN = (
    'Godot Engine v4.7.2.stable.official.ed1daf0bf - https://godotengine.org\n'
    '\n'
    'A3d resolver inventory: 45720 cases; 3690 candidates without exits\n'
    'A3d settled inventory: 9144 accepted exchanges\n'
    'Mount slice PASS: 256992 assertions\n'
)

# Abridged output of a real mutant run (`BjjGrade.successful` gate removed): a
# production assert aborted one test function, yet Godot printed PASS and
# exited 0 with only 67139 assertions (the last two backtrace lines are omitted).
REAL_PREMATURE = (
    'Godot Engine v4.7.2.stable.official.ed1daf0bf - https://godotengine.org\n'
    '\n'
    'A3d settled inventory: 9144 accepted exchanges\n'
    'Mount slice PASS: 67139 assertions\n'
    'SCRIPT ERROR: Assertion failed: Missing exit-map destination for escape\n'
    '          at: resolve_action (res://scripts/positions/mount/mount_resolver.gd:64)\n'
    '          GDScript backtrace (most recent call first):\n'
    '              [0] resolve_action (res://scripts/positions/mount/mount_resolver.gd:64)\n'
    '              [1] _test_exit_inventory_resolver (res://tests/test_mount_slice.gd:300)\n'
    '              [2] _initialize (res://tests/test_mount_slice.gd:14)\n'
    "SCRIPT ERROR: Invalid access to property or key 'final_grade' on a base object of type 'Dictionary'.\n"
    '          at: _test_exit_inventory_resolver (res://tests/test_mount_slice.gd:302)\n'
)

# Output shape of a run that records assertion failures (test calls quit(1)).
FAILING_RUN = (
    'Godot Engine v4.7.2.stable.official.ed1daf0bf - https://godotengine.org\n'
    '\n'
    'FAIL catalog mount.bottom.elbow_knee_escape grade=2 band=0: got Half Guard; expected Open Guard\n'
    'ERROR: Mount slice: 1684 / 256990 assertions failed\n'
)


def clean_with(extra_line, position=-1):
    lines = REAL_CLEAN.splitlines()
    lines.insert(position, extra_line)
    return '\n'.join(lines) + '\n'


class ValidatorTests(unittest.TestCase):
    def assertRejected(self, text, exit_code=0, fragment=''):
        self.assertTrue(fragment, 'a rejection fragment is required')
        problems = validate(text, exit_code, EXPECTED)
        self.assertTrue(problems, 'log was accepted: ' + repr(text))
        self.assertTrue(any(fragment in problem for problem in problems), (fragment, problems))

    def test_real_clean_log_is_accepted(self):
        self.assertEqual(validate(REAL_CLEAN, 0, EXPECTED), [])

    def test_crlf_and_ansi_wrapped_clean_log_is_accepted(self):
        self.assertEqual(validate(REAL_CLEAN.replace('\n', '\r\n'), 0, EXPECTED), [])
        self.assertEqual(validate(REAL_CLEAN.replace('Mount slice PASS: 256992 assertions',
                                                      '\x1b[32mMount slice PASS: 256992 assertions\x1b[0m'), 0, EXPECTED), [])

    def test_zero_exit_with_premature_pass_is_rejected(self):
        problems = validate(REAL_PREMATURE, 0, EXPECTED)
        joined = '\n'.join(problems)
        self.assertIn('assertion count 67139 != required 256992', joined)
        self.assertIn('SCRIPT ERROR: Assertion failed', joined)

    def test_premature_pass_without_any_other_diagnostic_is_rejected_by_count_alone(self):
        text = REAL_CLEAN.replace('256992', '67139')
        self.assertRejected(text, fragment='assertion count 67139')

    def test_count_must_match_exactly_in_both_directions(self):
        self.assertRejected(REAL_CLEAN.replace('256992', '256991'), fragment='256991')
        self.assertRejected(REAL_CLEAN.replace('256992', '256993'), fragment='256993')

    def test_missing_pass_and_empty_or_truncated_output_are_rejected(self):
        self.assertRejected('', fragment='missing')
        self.assertRejected('\n\n', fragment='missing')
        truncated = ''.join(REAL_CLEAN.splitlines(True)[:3])
        self.assertRejected(truncated, fragment='missing')
        self.assertRejected(REAL_CLEAN.replace('Mount slice PASS: 256992 assertions\n', 'Mount slice PASS: 2569'), fragment='malformed')

    def test_duplicate_completion_lines_are_rejected(self):
        self.assertRejected(clean_with('Mount slice PASS: 256992 assertions'), fragment='2 times')
        self.assertRejected(clean_with('Mount slice PASS: 67139 assertions', 2), fragment='2 times')

    def test_malformed_completion_lines_are_rejected(self):
        for bad in ('Mount slice PASS: 256,992 assertions', 'Mount slice PASS: 0256992 assertions',
                    'Mount slice PASS: 256992', 'Mount slice PASS: 256992 assertions extra',
                    'Mount slice PASS:  256992 assertions', 'Mount slice PASS: 0 assertions',
                    'Mount slice PASS: -5 assertions', 'mount slice pass: 256992 assertions',
                    ' Mount slice PASS: 256992 assertions', 'Mount slice PASS: assertions'):
            with self.subTest(bad=bad):
                text = REAL_CLEAN.replace('Mount slice PASS: 256992 assertions', bad)
                self.assertRejected(text, fragment='malformed')

    def test_nonzero_exit_is_rejected_even_with_a_perfect_log(self):
        self.assertRejected(REAL_CLEAN, exit_code=1, fragment='status 1')
        self.assertRejected(REAL_CLEAN, exit_code=-11, fragment='status -11')
        self.assertRejected(REAL_CLEAN, exit_code=139, fragment='status 139')

    def test_each_unexpected_diagnostic_form_is_rejected(self):
        for line in ('ERROR: something unexpected', 'WARNING: something unexpected',
                     'SCRIPT ERROR: Parse Error: nope', 'USER ERROR: nope', 'USER WARNING: nope',
                     'SHADER ERROR: nope', 'EDITOR ERROR: nope', '  ERROR: indented',
                     'FAIL some case: got 1; expected 2', 'ERROR: Mount slice: 1 / 5 assertions failed',
                     'Mount slice: 1 / 5 assertions failed', 'Parse Error: Identifier not found',
                     'GDScript backtrace (most recent call first):', 'Program crashed with signal 11',
                     'Traceback (most recent call last):', 'SCRIPT ERROR: Assertion failed: x'):
            for position in (2, -1):
                with self.subTest(line=line, position=position):
                    self.assertRejected(clean_with(line, position), fragment='unexpected diagnostic')

    def test_diagnostics_after_a_perfect_count_and_exit_zero_are_rejected(self):
        # A failing callee assert need not abort its caller: count and exit stay perfect.
        for line in ('SCRIPT ERROR: Assertion failed: Missing exit-map destination',
                     'ERROR: late', 'WARNING: late', 'USER ERROR: late'):
            with self.subTest(line=line):
                self.assertRejected(REAL_CLEAN + line + '\n', fragment='unexpected diagnostic')

    def test_diagnostics_glued_to_another_line_are_rejected(self):
        for glued in ('A3d settled inventory: 9144 accepted exchangesSCRIPT ERROR: boom',
                      'A3d settled inventory: 9144 accepted exchangesERROR: boom',
                      'foo WARNING: boom', '\ufeffERROR: boom', '\x00ERROR: boom'):
            with self.subTest(glued=glued):
                self.assertRejected(clean_with(glued, 3), fragment='unexpected diagnostic')

    def test_lowercase_prose_mentioning_error_is_not_a_diagnostic(self):
        self.assertEqual(validate(clean_with('no error: all good'), 0, EXPECTED), [])

    def test_real_failing_run_is_rejected_with_exit_and_diagnostics(self):
        problems = validate(FAILING_RUN, 1, EXPECTED)
        joined = '\n'.join(problems)
        for fragment in ('status 1', 'FAIL catalog', 'assertions failed', 'missing'):
            self.assertIn(fragment, joined)

    def test_benign_a3d_summary_lines_are_not_diagnostics(self):
        text = REAL_CLEAN + 'A3d resolver inventory: 45720 cases; 3690 candidates without exits\n'
        self.assertEqual(validate(text, 0, EXPECTED), [])

    def test_many_diagnostics_are_summarised(self):
        text = REAL_CLEAN + 'ERROR: x\n' * 20
        problems = validate(text, 0, EXPECTED)
        self.assertLessEqual(len(problems), 7)
        self.assertTrue(any('15 more' in problem for problem in problems))


class CommandLineTests(unittest.TestCase):
    def run_cli(self, text, *args, name='mount.log'):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / name
            if text is not None:
                path.write_text(text)
            return subprocess.run([sys.executable, '-I', str(Path(__file__).with_name('validate_mount_slice_log.py')),
                                   str(path), *args], capture_output=True, text=True)

    def test_exit_codes_and_messages(self):
        good = self.run_cli(REAL_CLEAN, '--exit-code', '0', '--expected-assertions', str(EXPECTED))
        self.assertEqual((good.returncode, good.stderr), (0, ''))
        self.assertIn('OK', good.stdout)
        bad = self.run_cli(REAL_PREMATURE, '--exit-code', '0', '--expected-assertions', str(EXPECTED))
        self.assertEqual(bad.returncode, 1)
        self.assertIn('INVALID', bad.stderr)
        self.assertIn('67139', bad.stderr)
        self.assertEqual(self.run_cli(REAL_CLEAN, '--exit-code', '1', '--expected-assertions', str(EXPECTED)).returncode, 1)

    def test_unreadable_log_and_bad_arguments_fail_closed(self):
        self.assertEqual(self.run_cli(None, '--exit-code', '0', '--expected-assertions', str(EXPECTED)).returncode, 1)
        self.assertNotEqual(self.run_cli(REAL_CLEAN, '--expected-assertions', str(EXPECTED)).returncode, 0)
        self.assertNotEqual(self.run_cli(REAL_CLEAN, '--exit-code', '0').returncode, 0)
        self.assertNotEqual(self.run_cli(REAL_CLEAN, '--exit-code', '0', '--expected-assertions', '0').returncode, 0)
        self.assertNotEqual(self.run_cli(REAL_CLEAN, '--exit-code', 'x', '--expected-assertions', '5').returncode, 0)

    def test_binary_and_directory_logs_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / 'binary.log'
            binary.write_bytes(b'\xff\xfe\x00garbage')
            args = ('--exit-code', '0', '--expected-assertions', str(EXPECTED))
            script = str(Path(__file__).with_name('validate_mount_slice_log.py'))
            for target in (binary, Path(directory)):
                result = subprocess.run([sys.executable, '-I', script, str(target), *args], capture_output=True, text=True)
                self.assertEqual(result.returncode, 1, (target, result.stderr))
                self.assertIn('INVALID', result.stderr)

    def test_main_accepts_argv_in_process(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'mount.log'
            path.write_text(REAL_CLEAN)
            self.assertEqual(main([str(path), '--exit-code', '0', '--expected-assertions', str(EXPECTED)]), 0)
            with contextlib.redirect_stderr(io.StringIO()) as captured:
                self.assertEqual(main([str(path), '--exit-code', '0', '--expected-assertions', '1']), 1)
            self.assertIn('256992 != required 1', captured.getvalue())


class WorkflowWiringTests(unittest.TestCase):
    """The step must keep calling the validator; a plain `godot ...` run is the vulnerability."""

    @staticmethod
    def mount_step():
        text = WORKFLOW.read_text()
        match = re.search(r'^      - name: Run frozen Mount-slice tests\n(.*?)(?=^      - name: )', text, re.S | re.M)
        assert match, 'Mount-slice step not found'
        return match.group(1)

    def test_mount_step_validates_exit_status_and_complete_log(self):
        step = self.mount_step()
        self.assertIn('res://tests/test_mount_slice.gd', step)
        self.assertIn('> /tmp/mount-slice.log 2>&1 || status=$?', step)
        self.assertIn('python tools/ci/validate_mount_slice_log.py /tmp/mount-slice.log --exit-code "$status" --expected-assertions', step)
        pin = re.search(r'--expected-assertions ([1-9][0-9]*)\s*$', step)
        self.assertIsNotNone(pin)
        self.assertEqual(int(pin.group(1)), EXPECTED, 'workflow pin and the test constant must change together')
        self.assertIn('shell: bash', step)
        self.assertIn('set -euo pipefail', step)
        for forbidden in ('continue-on-error', '\n        if:', 'set +e'):
            self.assertNotIn(forbidden, step)
        uncommented = [line for line in step.splitlines() if not line.lstrip().startswith('#')]
        self.assertTrue(any(line.lstrip().startswith('python tools/ci/validate_mount_slice_log.py') for line in uncommented),
                        'validator invocation must be live code, not a comment')

    def test_slice_script_is_run_exactly_once_by_the_validated_step(self):
        text = WORKFLOW.read_text()
        self.assertEqual(text.count('res://tests/test_mount_slice.gd'), 1)

    def test_stamina_read_only_diagnostic_step_is_untouched(self):
        text = WORKFLOW.read_text()
        self.assertIn("len(errors) == 2 and all(line.startswith('ERROR: read_only_property:') for line in errors)", text)


REGISTRY = 'Position registry'
REGISTRY_EXPECTED = 431
REGISTRY_CLEAN = (
    'Godot Engine v4.7.2.stable.official.ed1daf0bf - https://godotengine.org\n'
    '\n'
    'Position registry PASS: 431 assertions\n'
)
# Abridged real output of a registry mutant (`declared_ids` returned the read-only constant
# array): script errors aborted one test function, yet Godot printed PASS and exited 0.
REGISTRY_PREMATURE = (
    'Godot Engine v4.7.2.stable.official.ed1daf0bf - https://godotengine.org\n'
    '\n'
    'Position registry PASS: 379 assertions\n'
    'ERROR: Array is in read-only state.\n'
    '   at: push_back (core/variant/array.cpp:283)\n'
    '   GDScript backtrace (most recent call first):\n'
    '       [0] _test_duplicates_and_mutation_attempts (res://tests/test_position_registry.gd:120)\n'
    "SCRIPT ERROR: Invalid assignment on read-only value (on base: 'Array[String]').\n"
    '          at: _test_duplicates_and_mutation_attempts (res://tests/test_position_registry.gd:122)\n'
)


class NamedSuiteTests(unittest.TestCase):
    """The validator is shared by a second suite through --name; the default must not change."""

    def test_named_clean_log_is_accepted(self):
        self.assertEqual(validate(REGISTRY_CLEAN, 0, REGISTRY_EXPECTED, REGISTRY), [])

    def test_named_zero_exit_premature_pass_is_rejected(self):
        joined = '\n'.join(validate(REGISTRY_PREMATURE, 0, REGISTRY_EXPECTED, REGISTRY))
        self.assertIn('assertion count 379 != required 431', joined)
        self.assertIn('unexpected diagnostic: ERROR: Array is in read-only state.', joined)
        self.assertIn('SCRIPT ERROR: Invalid assignment', joined)

    def test_named_failures_missing_duplicate_malformed_and_exit(self):
        def rejected(text, fragment, code=0):
            problems = validate(text, code, REGISTRY_EXPECTED, REGISTRY)
            self.assertTrue(any(fragment in problem for problem in problems), (fragment, problems))
        rejected(REGISTRY_CLEAN.replace('Position registry PASS: 431 assertions\n', ''), 'missing')
        rejected(REGISTRY_CLEAN + 'Position registry PASS: 431 assertions\n', '2 times')
        rejected(REGISTRY_CLEAN.replace('431 assertions', '431 checks'), 'malformed')
        rejected(REGISTRY_CLEAN.replace('431', '40'), 'assertion count 40 != required 431')
        rejected(REGISTRY_CLEAN, 'status 1', code=1)
        rejected(REGISTRY_CLEAN + 'Position registry: 2 / 431 assertions failed\n', 'assertions failed')
        rejected(REGISTRY_CLEAN + 'ERROR: late\n', 'unexpected diagnostic')

    def test_suites_never_accept_each_others_completion_lines(self):
        self.assertTrue(validate(REAL_CLEAN, 0, EXPECTED, REGISTRY))
        self.assertTrue(validate(REGISTRY_CLEAN, 0, REGISTRY_EXPECTED))
        self.assertTrue(any('missing' in problem for problem in validate(REGISTRY_CLEAN, 0, REGISTRY_EXPECTED)))

    def test_name_with_regex_metacharacters_is_matched_literally(self):
        text = 'A.B (x) PASS: 5 assertions\n'
        self.assertEqual(validate(text, 0, 5, 'A.B (x)'), [])
        self.assertTrue(validate('AxB (x) PASS: 5 assertions\n', 0, 5, 'A.B (x)'))

    def test_cli_name_option(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'registry.log'
            path.write_text(REGISTRY_CLEAN)
            script = str(Path(__file__).with_name('validate_mount_slice_log.py'))
            run = lambda *extra: subprocess.run([sys.executable, '-I', script, str(path), *extra], capture_output=True, text=True)
            good = run('--name', REGISTRY, '--exit-code', '0', '--expected-assertions', '431')
            self.assertEqual((good.returncode, good.stderr), (0, ''))
            self.assertIn('Position registry log OK', good.stdout)
            wrong_default = run('--exit-code', '0', '--expected-assertions', '431')
            self.assertEqual(wrong_default.returncode, 1)
            self.assertIn('Mount slice log INVALID', wrong_default.stderr)
            path.write_text(REGISTRY_PREMATURE)
            bad = run('--name', REGISTRY, '--exit-code', '0', '--expected-assertions', '431')
            self.assertEqual(bad.returncode, 1)
            self.assertIn('Position registry log INVALID', bad.stderr)
            for empty in ('', '   '):
                blank = run('--name', empty, '--exit-code', '0', '--expected-assertions', '431')
                self.assertEqual(blank.returncode, 2, blank.stderr)
                self.assertIn('--name must not be empty', blank.stderr)


class RegistryStepWiringTests(unittest.TestCase):
    @staticmethod
    def registry_step():
        text = WORKFLOW.read_text()
        match = re.search(r'^      - name: Validate canonical position registry[^\n]*\n(.*?)(?=^      - name: )', text, re.S | re.M)
        assert match, 'registry step not found'
        return match.group(1)

    def test_step_validates_status_and_complete_log(self):
        step = self.registry_step()
        live = [line.strip() for line in step.splitlines() if line.strip() and not line.strip().startswith('#')]
        self.assertTrue(any(line.startswith('godot --headless --path GODOT_V1 --script res://tests/test_position_registry.gd '
                                            '> /tmp/position-registry.log 2>&1 || status=$?') for line in live), live)
        self.assertIn('set -euo pipefail', live)
        self.assertIn('shell: bash', live)
        pin = re.search(r'^\s*python tools/ci/validate_mount_slice_log\.py /tmp/position-registry\.log --name "Position registry" '
                        r'--exit-code "\$status" --expected-assertions ([1-9][0-9]*)\s*$', step, re.M)
        self.assertIsNotNone(pin, step)
        self.assertEqual(int(pin.group(1)), REGISTRY_EXPECTED, 'workflow pin and the test constant must change together')
        for forbidden in ('continue-on-error', '\n        if:', 'set +e'):
            self.assertNotIn(forbidden, step)

    def test_registry_script_is_run_exactly_once(self):
        self.assertEqual(WORKFLOW.read_text().count('res://tests/test_position_registry.gd'), 1)

    def test_pin_matches_the_gdscript_completion_contract(self):
        source = (WORKFLOW.parents[2] / 'GODOT_V1' / 'tests' / 'test_position_registry.gd').read_text()
        self.assertIn('print("Position registry PASS: %d assertions" % checks)', source)
        self.assertIn('push_error("Position registry: %d / %d assertions failed" % [failures, checks])', source)


FIGHTER = 'Fighter foundation'
FIGHTER_EXPECTED = 750


class FighterStepWiringTests(unittest.TestCase):
    @staticmethod
    def step():
        text = WORKFLOW.read_text()
        match = re.search(r'^      - name: Validate fighter definitions and read-only fighter snapshots[^\n]*\n(.*?)(?=^      - name: )', text, re.S | re.M)
        assert match, 'fighter foundation step not found'
        return match.group(1)

    def test_step_validates_status_and_complete_log(self):
        live = [line.strip() for line in self.step().splitlines() if line.strip() and not line.strip().startswith('#')]
        self.assertTrue(any(line.startswith('godot --headless --path GODOT_V1 --script res://tests/test_fighter_foundation.gd '
                                            '> /tmp/fighter-foundation.log 2>&1 || status=$?') for line in live), live)
        self.assertIn('set -euo pipefail', live)
        self.assertIn('shell: bash', live)
        pin = re.search(r'^\s*python tools/ci/validate_mount_slice_log\.py /tmp/fighter-foundation\.log --name "Fighter foundation" '
                        r'--exit-code "\$status" --expected-assertions ([1-9][0-9]*)\s*$', self.step(), re.M)
        self.assertIsNotNone(pin, self.step())
        self.assertEqual(int(pin.group(1)), FIGHTER_EXPECTED, 'workflow pin and the test constant must change together')
        for forbidden in ('continue-on-error', '\n        if:', 'set +e'):
            self.assertNotIn(forbidden, self.step())

    def test_script_runs_once_and_matches_the_completion_contract(self):
        self.assertEqual(WORKFLOW.read_text().count('res://tests/test_fighter_foundation.gd'), 1)
        source = (WORKFLOW.parents[2] / 'GODOT_V1' / 'tests' / 'test_fighter_foundation.gd').read_text()
        self.assertIn('print("Fighter foundation PASS: %d assertions" % checks)', source)
        self.assertIn('push_error("Fighter foundation: %d / %d assertions failed" % [failures, checks])', source)

    def test_validator_accepts_and_rejects_the_suite_log(self):
        clean = 'Godot Engine v4.7.2.stable.official.ed1daf0bf - https://godotengine.org\n\nFighter foundation PASS: 750 assertions\n'
        self.assertEqual(validate(clean, 0, FIGHTER_EXPECTED, FIGHTER), [])
        premature = clean.replace('750', '633') + 'SCRIPT ERROR: Invalid access to property or key on a base object of type Nil.\n'
        joined = '\n'.join(validate(premature, 0, FIGHTER_EXPECTED, FIGHTER))
        self.assertIn('assertion count 633 != required 750', joined)
        self.assertIn('unexpected diagnostic', joined)
        self.assertTrue(validate(clean.replace('Fighter foundation PASS', 'Position registry PASS'), 0, FIGHTER_EXPECTED, FIGHTER))


PRACTICE = 'Mount practice'
PRACTICE_EXPECTED = 1036


class PracticeStepWiringTests(unittest.TestCase):
    @staticmethod
    def step():
        text = WORKFLOW.read_text()
        match = re.search(r'^      - name: Validate the 2D Mount practice scene[^\n]*\n(.*?)(?=^      - name: )', text, re.S | re.M)
        assert match, 'practice step not found'
        return match.group(1)

    def test_step_validates_status_and_complete_log(self):
        live = [line.strip() for line in self.step().splitlines() if line.strip() and not line.strip().startswith('#')]
        self.assertTrue(any(line.startswith('godot --headless --path GODOT_V1 --script res://tests/test_mount_practice.gd '
                                            '> /tmp/mount-practice.log 2>&1 || status=$?') for line in live), live)
        self.assertIn('set -euo pipefail', live)
        self.assertIn('shell: bash', live)
        pin = re.search(r'^\s*python tools/ci/validate_mount_slice_log\.py /tmp/mount-practice\.log --name "Mount practice" '
                        r'--exit-code "\$status" --expected-assertions ([1-9][0-9]*)\s*$', self.step(), re.M)
        self.assertIsNotNone(pin, self.step())
        self.assertEqual(int(pin.group(1)), PRACTICE_EXPECTED, 'workflow pin and the test constant must change together')
        for forbidden in ('continue-on-error', '\n        if:', 'set +e'):
            self.assertNotIn(forbidden, self.step())

    def test_script_runs_once_and_matches_the_completion_contract(self):
        self.assertEqual(WORKFLOW.read_text().count('res://tests/test_mount_practice.gd'), 1)
        source = (WORKFLOW.parents[2] / 'GODOT_V1' / 'tests' / 'test_mount_practice.gd').read_text()
        self.assertIn('print("Mount practice PASS: %d assertions" % checks)', source)
        self.assertIn('push_error("Mount practice: %d / %d assertions failed" % [failures, checks])', source)

    def test_regression_pins_of_the_earlier_suites_are_untouched(self):
        text = WORKFLOW.read_text()
        for name, count in (('/tmp/mount-slice.log', 256992), ('/tmp/position-registry.log', 431), ('/tmp/fighter-foundation.log', 750)):
            self.assertRegex(text, r'validate_mount_slice_log\.py %s [^\n]*--expected-assertions %d\n' % (re.escape(name), count))

    def test_default_scene_is_the_practice_scene_and_the_3d_greybox_is_kept(self):
        project = (WORKFLOW.parents[2] / 'GODOT_V1' / 'project.godot').read_text()
        self.assertIn('run/main_scene="res://scenes/mount_practice.tscn"', project)
        self.assertTrue((WORKFLOW.parents[2] / 'GODOT_V1' / 'scenes' / 'mount_debug.tscn').is_file())
        self.assertIn('Smoke-test the default scene', WORKFLOW.read_text())

    def test_validator_rejects_a_premature_practice_log(self):
        clean = 'Godot Engine v4.7.2.stable.official.ed1daf0bf - https://godotengine.org\n\nMount practice PASS: 1036 assertions\n'
        self.assertEqual(validate(clean, 0, PRACTICE_EXPECTED, PRACTICE), [])
        premature = clean.replace('1036', '700') + 'SCRIPT ERROR: Invalid access to property or key.\n'
        joined = '\n'.join(validate(premature, 0, PRACTICE_EXPECTED, PRACTICE))
        self.assertIn('assertion count 700 != required 1036', joined)
        self.assertIn('unexpected diagnostic', joined)


class _HalfGuardSuiteWiring:
    """Shared wiring checks for the three Half Guard Godot suites (each is its own workflow step with an exact pin)."""
    NAME = ''
    STEP_PREFIX = ''
    SCRIPT = ''
    LOG = ''
    EXPECTED = 0

    @classmethod
    def step(cls):
        text = WORKFLOW.read_text()
        match = re.search(r'^      - name: %s[^\n]*\n(.*?)(?=^      - name: )' % re.escape(cls.STEP_PREFIX), text, re.S | re.M)
        assert match, '%s step not found' % cls.NAME
        return match.group(1)

    def test_step_validates_status_and_complete_log(self):
        live = [line.strip() for line in self.step().splitlines() if line.strip() and not line.strip().startswith('#')]
        self.assertTrue(any(line.startswith('godot --headless --path GODOT_V1 --script res://tests/%s > %s 2>&1 || status=$?' % (self.SCRIPT, self.LOG))
                            for line in live), live)
        self.assertIn('set -euo pipefail', live)
        self.assertIn('shell: bash', live)
        pin = re.search(r'^\s*python tools/ci/validate_mount_slice_log\.py %s --name "%s" --exit-code "\$status" --expected-assertions ([1-9][0-9]*)\s*$'
                        % (re.escape(self.LOG), re.escape(self.NAME)), self.step(), re.M)
        self.assertIsNotNone(pin, self.step())
        self.assertEqual(int(pin.group(1)), self.EXPECTED, 'workflow pin and the test constant must change together')
        for forbidden in ('continue-on-error', '\n        if:', 'set +e'):
            self.assertNotIn(forbidden, self.step())

    def test_script_runs_once_and_matches_the_completion_contract(self):
        self.assertEqual(WORKFLOW.read_text().count('res://tests/' + self.SCRIPT), 1)
        source = (WORKFLOW.parents[2] / 'GODOT_V1' / 'tests' / self.SCRIPT).read_text()
        self.assertIn('print("%s PASS: %%d assertions" %% checks)' % self.NAME, source)
        self.assertIn('push_error("%s: %%d / %%d assertions failed" %% [failures, checks])' % self.NAME, source)

    def test_validator_accepts_and_rejects_the_suite_log(self):
        clean = 'Godot Engine v4.7.2.stable.official.ed1daf0bf - https://godotengine.org\n\n%s PASS: %d assertions\n' % (self.NAME, self.EXPECTED)
        self.assertEqual(validate(clean, 0, self.EXPECTED, self.NAME), [])
        premature = clean.replace(str(self.EXPECTED), '7') + 'SCRIPT ERROR: Invalid access to property or key on a base object of type Nil.\n'
        joined = '\n'.join(validate(premature, 0, self.EXPECTED, self.NAME))
        self.assertIn('assertion count 7 != required %d' % self.EXPECTED, joined)
        self.assertIn('unexpected diagnostic', joined)
        self.assertTrue(validate(clean.replace(self.NAME + ' PASS', 'Position registry PASS'), 0, self.EXPECTED, self.NAME))


class HalfGuardBoundariesWiringTests(_HalfGuardSuiteWiring, unittest.TestCase):
    NAME, STEP_PREFIX = 'Half Guard boundaries', 'Validate Half Guard v0 boundaries'
    SCRIPT, LOG, EXPECTED = 'test_half_guard_boundaries.gd', '/tmp/half-guard-boundaries.log', 3999  # 4006 before B1h: the engine scope scan was revised on purpose


class HalfGuardReferenceWiringTests(_HalfGuardSuiteWiring, unittest.TestCase):
    NAME, STEP_PREFIX = 'Half Guard reference', 'Validate Half Guard v0 against the independent Python oracle'
    SCRIPT, LOG, EXPECTED = 'test_half_guard_reference.gd', '/tmp/half-guard-reference.log', 49609

    def test_fixture_is_generated_before_the_replay_and_by_the_oracle_only(self):
        text = WORKFLOW.read_text()
        generate = text.index('python GODOT_V1/tests/generate_half_guard_reference.py')
        replay = text.index('res://tests/test_half_guard_reference.gd')
        self.assertLess(generate, replay)
        self.assertEqual(text.count('generate_half_guard_reference.py'), 1)
        source = (WORKFLOW.parents[2] / 'GODOT_V1' / 'tests' / 'generate_half_guard_reference.py').read_text()
        self.assertIn('from oracles import half_guard_v0_scenarios', source)
        self.assertNotIn('bjj_game', source)


class HalfGuardConformanceWiringTests(_HalfGuardSuiteWiring, unittest.TestCase):
    NAME, STEP_PREFIX = 'Half Guard conformance', 'Validate Half Guard v0 window-gateway conformance'
    SCRIPT, LOG, EXPECTED = 'test_half_guard_conformance.gd', '/tmp/half-guard-conformance.log', 151


class HalfGuardEarlierPinsUntouchedTests(unittest.TestCase):
    def test_earlier_suite_pins_and_routing_inputs_are_untouched(self):
        text = WORKFLOW.read_text()
        for name, count in (('/tmp/mount-slice.log', 256992), ('/tmp/position-registry.log', 431), ('/tmp/fighter-foundation.log', 750),
                            ('/tmp/mount-practice.log', 1036)):
            self.assertRegex(text, r'validate_mount_slice_log\.py %s [^\n]*--expected-assertions %d\n' % (re.escape(name), count))


class HalfGuardMountEdgeWiringTests(_HalfGuardSuiteWiring, unittest.TestCase):
    NAME, STEP_PREFIX = 'Half Guard Mount edge', 'Validate the Half Guard v0 Mount edge adapter'
    SCRIPT, LOG, EXPECTED = 'test_half_guard_mount_edge.gd', '/tmp/half-guard-mount-edge.log', 3119

    def test_earlier_half_guard_pins_are_untouched(self):
        text = WORKFLOW.read_text()
        for name, count in (('/tmp/half-guard-boundaries.log', 3999), ('/tmp/half-guard-reference.log', 49609), ('/tmp/half-guard-conformance.log', 151)):
            self.assertRegex(text, r'validate_mount_slice_log\.py %s [^\n]*--expected-assertions %d\n' % (re.escape(name), count))


class HalfGuardGraphWiringTests(_HalfGuardSuiteWiring, unittest.TestCase):
    NAME, STEP_PREFIX = 'Half Guard graph', 'Validate the opt-in Mount to Half Guard graph integration'
    SCRIPT, LOG, EXPECTED = 'test_half_guard_graph.gd', '/tmp/half-guard-graph.log', 2133  # 2125 before B1i: the public-name scan checks the 8 new graph methods

    def test_earlier_pins_are_untouched(self):
        text = WORKFLOW.read_text()
        for name, count in (('/tmp/mount-slice.log', 256992), ('/tmp/position-registry.log', 431), ('/tmp/fighter-foundation.log', 750), ('/tmp/mount-practice.log', 1036),
                            ('/tmp/half-guard-boundaries.log', 3999), ('/tmp/half-guard-reference.log', 49609), ('/tmp/half-guard-conformance.log', 151),
                            ('/tmp/half-guard-mount-edge.log', 3119)):
            self.assertRegex(text, r'validate_mount_slice_log\.py %s [^\n]*--expected-assertions %d\n' % (re.escape(name), count))


class HalfGuardSealedProtocolWiringTests(_HalfGuardSuiteWiring, unittest.TestCase):
    NAME, STEP_PREFIX = 'Half Guard sealed protocol', 'Validate the Half Guard sealed-intent protocol'
    SCRIPT, LOG, EXPECTED = 'test_half_guard_sealed_protocol.gd', '/tmp/half-guard-sealed-protocol.log', 42309  # 41231 before B1h (GP-2/GP-3, published fallback)

    def test_earlier_pins_are_untouched(self):
        text = WORKFLOW.read_text()
        for name, count in (('/tmp/mount-slice.log', 256992), ('/tmp/position-registry.log', 431), ('/tmp/fighter-foundation.log', 750), ('/tmp/mount-practice.log', 1036),
                            ('/tmp/half-guard-boundaries.log', 3999), ('/tmp/half-guard-reference.log', 49609), ('/tmp/half-guard-conformance.log', 151),
                            ('/tmp/half-guard-mount-edge.log', 3119), ('/tmp/half-guard-graph.log', 2133)):
            self.assertRegex(text, r'validate_mount_slice_log\.py %s [^\n]*--expected-assertions %d\n' % (re.escape(name), count))


class HalfGuardFeintReferenceWiringTests(_HalfGuardSuiteWiring, unittest.TestCase):
    NAME, STEP_PREFIX = 'Half Guard feint reference', 'Validate Half Guard feints against the independent Python oracle'
    SCRIPT, LOG, EXPECTED = 'test_half_guard_feint_reference.gd', '/tmp/half-guard-feint-reference.log', 26415

    def test_feint_fixture_is_generated_before_the_replay_and_by_the_oracle_only(self):
        text = WORKFLOW.read_text()
        generate = text.index('python GODOT_V1/tests/generate_half_guard_feint_reference.py')
        replay = text.index('res://tests/test_half_guard_feint_reference.gd')
        self.assertLess(generate, replay)
        self.assertEqual(text.count('generate_half_guard_feint_reference.py'), 1)
        self.assertEqual(text.count('generate_half_guard_reference.py'), 1)  # the direct fixture generation step is untouched
        source = (WORKFLOW.parents[2] / 'GODOT_V1' / 'tests' / 'generate_half_guard_feint_reference.py').read_text()
        self.assertIn('from oracles import half_guard_v0_feint_scenarios', source)
        self.assertNotIn('bjj_game', source)


class HalfGuardFeintProtocolWiringTests(_HalfGuardSuiteWiring, unittest.TestCase):
    NAME, STEP_PREFIX = 'Half Guard feint protocol', 'Validate Half Guard feints through the sealed-intent protocol'
    SCRIPT, LOG, EXPECTED = 'test_half_guard_feint_protocol.gd', '/tmp/half-guard-feint-protocol.log', 32222

    def test_earlier_pins_are_untouched_except_the_two_intentional_b1h_revisions(self):
        text = WORKFLOW.read_text()
        for name, count in (('/tmp/mount-slice.log', 256992), ('/tmp/position-registry.log', 431), ('/tmp/fighter-foundation.log', 750), ('/tmp/mount-practice.log', 1036),
                            ('/tmp/half-guard-reference.log', 49609), ('/tmp/half-guard-conformance.log', 151), ('/tmp/half-guard-mount-edge.log', 3119),
                            ('/tmp/half-guard-graph.log', 2133),
                            ('/tmp/half-guard-boundaries.log', 3999), ('/tmp/half-guard-sealed-protocol.log', 42309)):
            self.assertRegex(text, r'validate_mount_slice_log\.py %s [^\n]*--expected-assertions %d\n' % (re.escape(name), count))


class HalfGuardGraphSealedFlowWiringTests(_HalfGuardSuiteWiring, unittest.TestCase):
    NAME, STEP_PREFIX = 'Half Guard graph sealed flow', 'Validate the opt-in sealed Half Guard graph match flow'
    SCRIPT, LOG, EXPECTED = 'test_half_guard_graph_sealed_flow.gd', '/tmp/half-guard-graph-sealed-flow.log', 2433

    def test_fixtures_used_by_the_flow_suite_are_generated_before_it(self):
        text = WORKFLOW.read_text()
        flow = text.index('res://tests/test_half_guard_graph_sealed_flow.gd')
        self.assertLess(text.index('python GODOT_V1/tests/generate_half_guard_reference.py'), flow)
        self.assertLess(text.index('python GODOT_V1/tests/generate_half_guard_feint_reference.py'), flow)

    def test_earlier_pins_are_untouched_except_the_b1i_graph_revision(self):
        text = WORKFLOW.read_text()
        for name, count in (('/tmp/mount-slice.log', 256992), ('/tmp/position-registry.log', 431), ('/tmp/fighter-foundation.log', 750), ('/tmp/mount-practice.log', 1036),
                            ('/tmp/half-guard-boundaries.log', 3999), ('/tmp/half-guard-reference.log', 49609), ('/tmp/half-guard-conformance.log', 151),
                            ('/tmp/half-guard-mount-edge.log', 3119), ('/tmp/half-guard-sealed-protocol.log', 42309), ('/tmp/half-guard-feint-reference.log', 26415),
                            ('/tmp/half-guard-feint-protocol.log', 32222), ('/tmp/half-guard-graph.log', 2133)):
            self.assertRegex(text, r'validate_mount_slice_log\.py %s [^\n]*--expected-assertions %d\n' % (re.escape(name), count))


if __name__ == '__main__':
    unittest.main()
