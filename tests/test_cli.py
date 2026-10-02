import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from bjj_game.interfaces.cli import main as bjj_main
from mount_v0.cli import _choose_entity, _print_summary, _read_input, _tee_to_log, main
from mount_v0.engine import MountRun
from mount_v0.model import EntityKind, Side


class CliTests(unittest.TestCase):
    def test_blank_action_input_repeats_menu_without_unknown_name_error(self):
        output = io.StringIO()
        with patch("builtins.input", side_effect=["", "1"]), redirect_stdout(output):
            entity = _choose_entity("TOP INITIATES", Side.TOP, EntityKind.ACTION)
        self.assertEqual(entity.canonical_name, "High Mount Climb")
        self.assertNotIn("Unknown Mount v0 name", output.getvalue())
        self.assertEqual(output.getvalue().count("TOP INITIATES"), 2)


    def test_summary_uses_short_names_instead_of_stable_ids(self):
        run = MountRun(initial_clock=10)
        run.history.initiated_action_history.append("mount.top.high_mount_climb")
        run.history.response_history.append("mount.bottom_response.forearm_frame")
        output = io.StringIO()
        with redirect_stdout(output):
            _print_summary(run)
        text = output.getvalue()
        self.assertIn("Initiated-action history: ['Climb High']", text)
        self.assertIn("Response history: ['Frame']", text)
        self.assertNotIn("mount.top.high_mount_climb", text)
        self.assertNotIn("mount.bottom_response.forearm_frame", text)

    def test_log_option_saves_printed_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "session.txt"
            terminal = io.StringIO()
            with redirect_stdout(terminal):
                code = main(["--check", "--log", str(path)])
            self.assertEqual(code, 0)
            self.assertTrue(path.exists())
            saved = path.read_text(encoding="utf-8")
            self.assertIn("LOG FILE:", saved)
            self.assertIn("STATUS: PASS", saved)
            self.assertIn("STATUS: PASS", terminal.getvalue())

    def test_cancelled_interactive_run_prints_partial_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cancelled.txt"
            terminal = io.StringIO()
            with patch("builtins.input", side_effect=["1", "1", KeyboardInterrupt]), redirect_stdout(terminal):
                code = main(["--clock", "0:10", "--interval", "5", "--log", str(path)])
            self.assertEqual(code, 130)
            saved = path.read_text(encoding="utf-8")
            self.assertIn("Run cancelled.", saved)
            self.assertIn("RUN SUMMARY", saved)
            self.assertIn("Run status: CANCELLED", saved)
            self.assertIn("Elapsed simulated time: 0:05", saved)
            self.assertIn("Exit reason: CANCELLED", saved)
            self.assertIn("Top behavior history: ['PRESSURE']", saved)
            self.assertIn("Bottom behavior history: ['ESCAPE']", saved)

    def test_eof_cancelled_interactive_run_prints_partial_summary(self):
        output = io.StringIO()
        with patch("builtins.input", side_effect=["1", EOFError]), redirect_stdout(output):
            code = main(["--clock", "0:10", "--interval", "5"])
        self.assertEqual(code, 130)
        text = output.getvalue()
        self.assertIn("Run status: CANCELLED", text)
        self.assertIn("Elapsed simulated time: 0:00", text)
        self.assertIn("Exit reason: CANCELLED", text)

    def test_read_input_mirrors_typed_text_to_log_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "input.txt"
            terminal = io.StringIO()
            with redirect_stdout(terminal):
                with _tee_to_log(path):
                    with patch("builtins.input", return_value="repummel"):
                        value = _read_input("> ")
            self.assertEqual(value, "repummel")
            saved = path.read_text(encoding="utf-8")
            self.assertIn("repummel\n", saved)
            self.assertNotIn("repummel", terminal.getvalue())

    def test_logged_blank_and_invalid_inputs_are_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "inputs.txt"
            terminal = io.StringIO()
            with patch("builtins.input", side_effect=["1", "1", "", "bogus", "1", "1", KeyboardInterrupt]), redirect_stdout(terminal):
                code = main(["--clock", "0:20", "--interval", "5", "--log", str(path)])
            self.assertEqual(code, 130)
            saved = path.read_text(encoding="utf-8")
            self.assertIn("> \n", saved)
            self.assertIn("> bogus\n", saved)
            self.assertIn("Unknown Mount v0 name: 'bogus'", saved)


    def test_primary_cli_defaults_medium_without_commitment_prompt_and_charges_stamina(self):
        output = io.StringIO()
        inputs = ["1", "1", "1", "2", KeyboardInterrupt]
        with patch("builtins.input", side_effect=inputs), redirect_stdout(output):
            code = bjj_main(["--clock", "0:10", "--interval", "5"])
        self.assertEqual(code, 130)
        text = output.getvalue()
        self.assertIn("MOUNT v0.1c — HOT-SEAT PROTOTYPE", text)
        self.assertIn("Standard commitment: MEDIUM", text)
        self.assertNotIn("\nCommitment\n", text)
        self.assertIn("Requested commitment: MEDIUM", text)
        self.assertIn("Effective commitment: MEDIUM", text)
        self.assertIn("Requested cost: 7", text)
        self.assertIn("Top: 100 → 99 (-1)", text)
        self.assertIn("Stamina after: 92", text)
        self.assertIn("Requested commitment history: ['MEDIUM']", text)
        self.assertIn("Effective commitment history: ['MEDIUM']", text)
        self.assertIn("Top stamina: 92/100 (Fresh)", text)

    def test_legacy_cli_has_no_commitment_prompt_or_stamina_cost(self):
        output = io.StringIO()
        inputs = ["1", "1", "1", "2", KeyboardInterrupt]
        with patch("builtins.input", side_effect=inputs), redirect_stdout(output):
            code = main(["--clock", "0:10", "--interval", "5"])
        self.assertEqual(code, 130)
        text = output.getvalue()
        self.assertIn("MOUNT v0 — HOT-SEAT PROTOTYPE", text)
        self.assertNotIn("\nCommitment\n", text)
        self.assertNotIn("CONSERVE", text)
        self.assertNotIn("Requested cost:", text)
        self.assertNotIn("BEHAVIOR STAMINA", text)
        self.assertIn("Top stamina: 100/100 (Fresh)", text)



if __name__ == "__main__":
    unittest.main()
