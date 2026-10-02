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
        self.assertIn("MOUNT v0.1e — HOT-SEAT PROTOTYPE", text)
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



    def test_blind_mode_locks_hidden_response_before_action(self):
        output = io.StringIO()
        inputs = ["1", "1", "1", KeyboardInterrupt]
        with (
            patch("builtins.input", side_effect=inputs),
            patch("bjj_game.interfaces.cli.getpass.getpass", return_value="1"),
            redirect_stdout(output),
        ):
            code = bjj_main(["--clock", "0:10", "--interval", "5", "--blind"])
        self.assertEqual(code, 130)
        text = output.getvalue()
        self.assertIn("Blind hot-seat testing:", text)
        response_index = text.index("BOTTOM RESPONSE — BLIND LOCK")
        action_index = text.index("TOP INITIATES")
        self.assertLess(response_index, action_index)
        self.assertIn("Response locked.", text)
        self.assertIn("Response: Forearm Frame", text)

    def test_blind_mode_reset_discards_locked_response_without_resolution(self):
        output = io.StringIO()
        inputs = ["3", "3", "4", KeyboardInterrupt]
        with (
            patch("builtins.input", side_effect=inputs),
            patch("bjj_game.interfaces.cli.getpass.getpass", return_value="1"),
            redirect_stdout(output),
        ):
            code = bjj_main(["--clock", "0:10", "--interval", "5", "--blind"])
        self.assertEqual(code, 130)
        text = output.getvalue()
        self.assertIn("BOTTOM RESPONSE — BLIND LOCK", text)
        self.assertIn("RESET / NO ACTION", text)
        self.assertIn("Response history: []", text)
        self.assertIn("Initiated-action history: []", text)



    def test_seeded_random_blind_responder_is_hidden_until_after_action(self):
        output = io.StringIO()
        inputs = ["1", "1", "2", KeyboardInterrupt]
        with patch("builtins.input", side_effect=inputs), redirect_stdout(output):
            code = bjj_main([
                "--clock", "0:10",
                "--interval", "5",
                "--blind",
                "--blind-responder", "random",
                "--seed", "42",
            ])
        self.assertEqual(code, 130)
        text = output.getvalue()
        self.assertIn("Random blind responder seed: 42", text)
        self.assertIn("Random blind Bottom response mix: Frame=4, Tight Elbows=3", text)
        self.assertIn("Random blind Top response mix: Wide Base=2, Hip Follow=1", text)

        lock_index = text.index("BOTTOM RESPONSE — RANDOM BLIND LOCK")
        action_index = text.index("TOP INITIATES")
        reveal_index = text.index("RANDOM BLIND RESPONSE #1: Tight-Elbow Arm Defense")
        self.assertLess(lock_index, action_index)
        self.assertGreater(reveal_index, action_index)
        self.assertIn("[draw 5/6]", text)

    def test_seeded_random_blind_reset_logs_unused_choice_after_reset(self):
        output = io.StringIO()
        inputs = ["3", "3", "4", KeyboardInterrupt]
        with patch("builtins.input", side_effect=inputs), redirect_stdout(output):
            code = bjj_main([
                "--clock", "0:10",
                "--interval", "5",
                "--blind",
                "--blind-responder", "random",
                "--seed", "42",
            ])
        self.assertEqual(code, 130)
        text = output.getvalue()
        reset_index = text.index("RESET / NO ACTION")
        reveal_index = text.index(
            "RANDOM BLIND RESPONSE #1 UNUSED (RESET): Tight-Elbow Arm Defense"
        )
        self.assertGreater(reveal_index, reset_index)
        self.assertIn("Response history: []", text)


    def test_random_blind_session_log_contains_seed_and_choice(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "random-blind.txt"
            terminal = io.StringIO()
            inputs = ["1", "1", "2", KeyboardInterrupt]
            with patch("builtins.input", side_effect=inputs), redirect_stdout(terminal):
                code = bjj_main([
                    "--clock", "0:10",
                    "--interval", "5",
                    "--blind",
                    "--blind-responder", "random",
                    "--seed", "42",
                    "--log", str(path),
                ])
            self.assertEqual(code, 130)
            saved = path.read_text(encoding="utf-8")
            self.assertIn("Random blind responder seed: 42", saved)
            self.assertIn(
                "RANDOM BLIND RESPONSE #1: Tight-Elbow Arm Defense [draw 5/6]",
                saved,
            )


    def test_random_blind_requires_blind_and_seed(self):
        output = io.StringIO()
        with redirect_stdout(output):
            code = bjj_main(["--blind-responder", "random", "--seed", "42"])
        self.assertEqual(code, 2)
        self.assertIn("--blind-responder random requires --blind", output.getvalue())

        output = io.StringIO()
        with redirect_stdout(output):
            code = bjj_main(["--blind", "--blind-responder", "random"])
        self.assertEqual(code, 2)
        self.assertIn("--blind-responder random requires --seed N", output.getvalue())

    def test_seed_rejected_without_random_blind_responder(self):
        output = io.StringIO()
        with redirect_stdout(output):
            code = bjj_main(["--blind", "--seed", "42"])
        self.assertEqual(code, 2)
        self.assertIn("--seed is only valid with --blind-responder random", output.getvalue())



    def test_fixed_behavior_flags_remove_behavior_prompts(self):
        output = io.StringIO()
        inputs = ["4", KeyboardInterrupt]
        with patch("builtins.input", side_effect=inputs), redirect_stdout(output):
            code = bjj_main([
                "--clock", "0:10",
                "--interval", "5",
                "--top-behavior", "PRESSURE",
                "--bottom-behavior", "ESCAPE",
            ])
        self.assertEqual(code, 0)
        text = output.getvalue()
        self.assertIn("Top behavior fixed for session: PRESSURE", text)
        self.assertIn("Bottom behavior fixed for session: ESCAPE", text)
        self.assertNotIn("\nTop behavior\n", text)
        self.assertNotIn("\nBottom behavior\n", text)
        self.assertIn("Top behavior history: ['PRESSURE', 'PRESSURE']", text)
        self.assertIn("Bottom behavior history: ['ESCAPE', 'ESCAPE']", text)

    def test_one_fixed_behavior_leaves_other_side_interactive(self):
        output = io.StringIO()
        inputs = ["1", "4", KeyboardInterrupt]
        with patch("builtins.input", side_effect=inputs), redirect_stdout(output):
            code = bjj_main([
                "--clock", "0:10",
                "--interval", "5",
                "--top-behavior", "HOLD",
            ])
        self.assertEqual(code, 130)
        text = output.getvalue()
        self.assertIn("Top behavior fixed for session: HOLD", text)
        self.assertNotIn("\nTop behavior\n", text)
        self.assertIn("\nBottom behavior\n", text)


    def test_primary_cli_can_reset_without_response_or_action_cost(self):
        output = io.StringIO()
        inputs = ["3", "3", "4", KeyboardInterrupt]
        with patch("builtins.input", side_effect=inputs), redirect_stdout(output):
            code = bjj_main(["--clock", "0:10", "--interval", "5"])
        self.assertEqual(code, 130)
        text = output.getvalue()
        self.assertIn("RESET / NO ACTION", text)
        self.assertIn("Action stamina cost: 0", text)
        self.assertIn("Initiative passes to: Bottom", text)
        self.assertNotIn("BOTTOM RESPONSE", text)
        self.assertIn("Reset / no-action history: ['top']", text)


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




    def test_legacy_cli_rejects_blind_testing_flag(self):
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(["--blind"])
        self.assertEqual(code, 2)
        self.assertIn("modern playtest flags", output.getvalue())



    def test_legacy_cli_rejects_fixed_behavior_flags(self):
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(["--top-behavior", "PRESSURE"])
        self.assertEqual(code, 2)
        self.assertIn("modern playtest flags", output.getvalue())


    def test_primary_check_reports_commitment_dominance_and_visibility_debt(self):
        output = io.StringIO()
        with redirect_stdout(output):
            code = bjj_main(["--check"])
        self.assertEqual(code, 0)
        text = output.getvalue()
        self.assertIn("COMMITMENT DOMINANCE: LOW strictly dominates", text)
        self.assertIn("COMMITMENT VISIBILITY: public in v0.1e", text)
        self.assertIn("STAMINA PACING LOW", text)
        self.assertIn("Exhausted Top 2:30, Bottom 2:30", text)
        self.assertIn("STAMINA PACING MEDIUM", text)
        self.assertIn("Exhausted Top 1:25, Bottom 1:30", text)
        self.assertIn("STAMINA PACING HIGH", text)
        self.assertIn("Exhausted Top 0:55, Bottom 1:00", text)
        self.assertIn("CONSERVE CYCLE NET (10s): LOW +1, MEDIUM -3, HIGH -8; RESET +4", text)
        self.assertIn("EXHAUSTION HYSTERESIS: enter Exhausted at <=25; recover only at >=35", text)
        self.assertIn(
            "EXHAUSTED REACHABILITY: Elbow-Knee Escape / Top PRESSURE: Half Guard=+0.10..+1.10; Open Guard=UNREACHABLE",
            text,
        )
        self.assertIn(
            "EXHAUSTED REACHABILITY: Trap-and-Roll Escape / Top HOLD: Reversal=UNREACHABLE",
            text,
        )
        self.assertIn("V0.2 RESPONSE-STAMINA DEBT", text)
        self.assertIn("RESET/STALLING DEBT", text)
        self.assertIn(
            "RESET LOCK PROBE: Top PRESSURE+RESET vs Bottom ESCAPE+RESET -> TIMEOUT — Mount retained; axis +4.00; band Locked; Top stamina 40; Bottom stamina 40",
            text,
        )
        self.assertIn("BLIND PLAYTEST MODE: use --blind", text)
        self.assertIn(
            "RANDOM BLIND RESPONDER MIX: Bottom Frame=4, Tight Elbows=3; Top Wide Base=2, Hip Follow=1",
            text,
        )
        self.assertIn("BLIND MIX BAND METRICS", text)
        self.assertIn(
            "BLIND MIX: Bottom / Strong / Elbow-Knee Escape: raw attacker-axis "
            "-0.667; realized-axis -0.667..-0.270; escape 0.0%",
            text,
        )

    def test_legacy_check_does_not_report_v01_commitment_diagnostics(self):
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(["--check"])
        self.assertEqual(code, 0)
        text = output.getvalue()
        self.assertNotIn("COMMITMENT DOMINANCE", text)
        self.assertNotIn("COMMITMENT VISIBILITY", text)
        self.assertNotIn("CONSERVE CYCLE NET", text)
        self.assertNotIn("EXHAUSTION HYSTERESIS", text)
        self.assertNotIn("EXHAUSTED REACHABILITY", text)
        self.assertNotIn("V0.2 RESPONSE-STAMINA DEBT", text)
        self.assertNotIn("RESET/STALLING DEBT", text)
        self.assertNotIn("RESET LOCK PROBE", text)
        self.assertNotIn("BLIND PLAYTEST MODE", text)
        self.assertNotIn("RANDOM BLIND RESPONDER MIX", text)
        self.assertNotIn("BLIND MIX BAND METRICS", text)



if __name__ == "__main__":
    unittest.main()
